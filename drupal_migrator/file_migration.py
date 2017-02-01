""" migrate Drupal filesystem data into the new library structure """

from library.models import Codebase, CodebaseRelease
from library import fs
from .database_migration import IDMapper
from .utils import get_first_field
from django.contrib.auth.models import User
from typing import Dict
from urllib.parse import urlparse

import datetime
import filecmp
import os
import json
import shutil
import re
import logging
import pygit2


logger = logging.getLogger(__name__)


class ModelVersionFileset:

    OPENABM_VERSIONDIRS_MAP = {
        'dataset': 'data',
        'sensitivity': 'results'
        # one to one mappings for doc and code
    }

    def __init__(self, basedir, version_number: int):
        self.basedir = basedir
        self.semver = '1.{0}.0'.format(version_number - 1)

    def migrate(self, release: CodebaseRelease):
        working_directory_path = str(release.workdir_path)
        submitted_package_path = str(release.submitted_package_path())
        # copy basedirs over verbatim into the working directory
        shutil.copytree(self.basedir, working_directory_path)
        # scan workdir path for hidden files that should be deleted
        for fdir in os.scandir(working_directory_path):
            # this version directory may have code/ doc/ dataset/ sensitivity/ directories
            for f in os.scandir(fdir.path):
                logger.debug("inspecting file %s", f)
                if fs.is_archive(f.name):
                    logger.debug("unpacking %s to %s", f.path, submitted_package_path)
                    shutil.unpack_archive(f.path, submitted_package_path)
                else:
                    destination_dir = self.OPENABM_VERSIONDIRS_MAP.get(fdir.name, fdir.name)
                    destination_path = str(release.submitted_package_path(destination_dir))
                    os.makedirs(destination_path, exist_ok=True)
                    shutil.copy(f.path, destination_path)

        for root, dirs, files in os.walk(submitted_package_path, topdown=True):
            if root == '__MACOSX':
                logger.debug("deleting mac os x system directory")
                shutil.rmtree(root)
                continue
            for f in files:
                if fs.is_system_file(f):
                    logger.debug("deleting system file %s", f)
                    os.remove(os.path.join(root, f))


class ModelFileset:

    VERSION_REGEX = re.compile('\d+')

    def __init__(self, model_id: int, dir_entry):
        self._model_id = model_id
        self._dir_entry = dir_entry
        self._versions = []
        self._media = []
        for f in os.scandir(dir_entry.path):
            vd = f.is_dir() and self.is_version_dir(f.name)
            if vd:
                self._versions.append(ModelVersionFileset(f.path, int(vd.group(0))))
            elif fs.is_media(f.path):
                self._media.append(f)
            else:
                logger.debug("What is this abomination? %s", f)

    @staticmethod
    def is_version_dir(candidate: str):
        return candidate.startswith('v') and ModelFileset.VERSION_REGEX.search(candidate)

    def migrate(self):
        codebase = Codebase.objects.get(identifier=self._model_id)
        for version in self._versions:
            logger.debug("looking for version %s in codebase %s", version.semver, codebase)
            release = codebase.releases.get(version_number=version.semver)
            version.migrate(release)
        media_dir = str(codebase.media_dir())
        os.makedirs(media_dir, exist_ok=True)
        for media_dir_entry in self._media:
            shutil.copy(media_dir_entry.path, media_dir)
            codebase.images.append({
                'name': media_dir_entry.name,
                'path': media_dir,
                'url': codebase.media_url(media_dir_entry.name),
            })
        codebase.save()



def load(src_dir: str):
    logger.debug("LOADING FROM %s", src_dir)
    shutil.register_unpack_format('rar', ['.rar'], fs.unrar)
    for dir_entry in os.scandir(src_dir):
        if dir_entry.is_dir():
            try:
                model_id = int(dir_entry.name)
                logger.debug("processing %s", dir_entry.path)
                mfs = ModelFileset(model_id, dir_entry)
                mfs.migrate()
            except:
                logger.exception("Unmodel-library-like file: %s", dir_entry.name)


class ModelVersionFiles:
    def __init__(self, origin_folder: str, destination_folder: str, code: str, dataset: str, addfiles: str,
                 sensitivity: str, documentation: str):
        self.destination_folder = destination_folder
        self.origin_folder = origin_folder
        self.code = code
        self.dataset = dataset
        self.addfiles = addfiles
        self.sensitivity = sensitivity
        self.documentation = documentation

    @classmethod
    def from_raw_model_version(cls, origin_folder, destination_folder, raw_model_version: Dict):
        code = cls.transform_uri(get_first_field(raw_model_version, 'field_modelversion_code', 'uri'))
        dataset = cls.transform_uri(get_first_field(raw_model_version, 'field_modelversion_dataset', 'uri'))
        addfiles = cls.transform_uri(get_first_field(raw_model_version, 'field_modelversion_addfiles', 'uri'))
        sensitivity = cls.transform_uri(get_first_field(raw_model_version, 'field_modelversion_sensitivity', 'uri'))
        documentation = cls.transform_uri(get_first_field(raw_model_version, 'field_modelversion_documentation', 'uri'))

        return cls(destination_folder, origin_folder, code, dataset, addfiles, sensitivity, documentation)

    @property
    def rel_paths(self):
        return [self.code, self.dataset, self.addfiles, self.sensitivity, self.documentation]

    @staticmethod
    def _extract_if_archive(full_path):
        import tarfile
        import zipfile

        archive = None
        if tarfile.is_tarfile(full_path):
            archive = tarfile.TarFile(full_path)
        elif zipfile.is_zipfile(full_path):
            archive = zipfile.ZipFile(full_path)

        if archive:
            archive.extractall()
            archive.close()
            shutil.rmtree(full_path)

    @staticmethod
    def patch_existing_file(origin_path, destination_path):
        with open(origin_path, 'rb') as origin_file:
            with open(destination_path, 'wb') as destination_file:
                destination_file.write(origin_file.read())

    @staticmethod
    def transform_uri(uri: str):
        return urlparse(uri).path or None

    def _extract_archives(self):
        for rel_path in self.rel_paths:
            self._extract_if_archive(os.path.join(self.origin_folder, rel_path))

    @classmethod
    def _update_or_create_files(cls, dcmp, origin_folder, destination_folder):
        """
        Recursively updates and creates files using a directory diff
        """
        for diff_file in dcmp.diff_files:
            cls.patch_existing_file(os.path.join(origin_folder, diff_file),
                                    os.path.join(destination_folder, diff_file))

        for new_file_or_directory in dcmp.right_only:
            shutil.copy(os.path.join(origin_folder, new_file_or_directory), destination_folder)

        for folder_name, sub_dcmp in dcmp.subdirs.items():
            cls._update_or_create_files(sub_dcmp,
                                        os.path.join(origin_folder, folder_name),
                                        os.path.join(destination_folder, folder_name))

    def update_or_create_files(self):
        self._extract_archives()
        dcmp = filecmp.dircmp(self.origin_folder, self.destination_folder)
        self._update_or_create_files(dcmp, self.origin_folder, self.destination_folder)


class ModelVersionMetadata:
    def __init__(self, language, language_version, license,
                 os, os_version,
                 platform, platform_version):
        self.language = language
        self.language_version = language_version
        self.license = license
        self.os = os
        self.os_version = os_version
        self.platform = platform
        self.platform_version = platform_version

    @classmethod
    def from_raw_model_version(cls, raw_model_version):
        language = get_first_field(raw_model_version, 'field_modelversion_language', 'value')
        language_version = get_first_field(raw_model_version, 'field_modelversion_language_ver', 'value')
        license = get_first_field(raw_model_version, 'field_modelversion_license', 'value')
        os = get_first_field(raw_model_version, 'field_modelversion_os', 'value')
        os_version = get_first_field(raw_model_version, 'field_modelversion_os_version', 'value')
        platform = get_first_field(raw_model_version, 'field_modelversion_platform', 'value')
        platform_version = get_first_field(raw_model_version, 'field_modelversion_platform_ver', 'value')

        return cls(language, language_version, license, os, os_version, platform, platform_version)

    @staticmethod
    def join(*args):
        return ' '.join([arg for arg in args if arg])

    def show(self):
        return json.dumps({
            'language': self.join(self.language, self.language_version),
            'license': self.license,
            'os': self.join(self.os, self.os_version),
            'platform': self.join(self.platform, self.platform_version)
        }, sort_keys=True, indent=4, separators=(',', ': '))


def sanitize_name(name: str) -> str:
    return re.sub(r"\W+", "_", name)


def create_repos(nid_to_id_mapper: IDMapper, json_dump_path: str, root_path: str, dest_path: str):
    """
    Creates git repos out of the files that are part of each of its model versions.

    :param nid_to_id_mapper: mapping between drupal ids and database ids
    :param json_dump_path: path to where the JSON dump of the Drupal DB is
    :param root_path: path to the root of where the OpenABM Drupal stores its files
    :param dest_path: path to where the Git Repos will be stored
    :return:
    """
    raw_model_versions = json.load(os.path.join(json_dump_path, 'ModelVersion.json'))

    id_models = Codebase.objects.in_bulk()

    for raw_model_version in raw_model_versions:
        drupal_model_id = get_first_field(raw_model_version, 'field_modelversion_model', 'nid')
        version_id = get_first_field(raw_model_version, 'field_modelversion_number', 'value')

        if drupal_model_id and version_id:
            id = nid_to_id_mapper[Codebase][drupal_model_id]
            model = id_models[id]
            creator = model.creator

            origin_folder = os.path.join(root_path, drupal_model_id, "v{}".format(version_id))
            destination_folder = os.path.join(dest_path, creator.get_full_name(),
                                              sanitize_name(model.title))

            repo = get_or_create_repo(destination_folder)
            model_version_files = ModelVersionFiles.from_raw_model_version(origin_folder=origin_folder,
                                                                           destination_folder=destination_folder,
                                                                           raw_model_version=raw_model_version)
            logger.debug("Preparing '{}' Version {} for update with Drupal ID: {}".format(
                destination_folder, version_id, drupal_model_id))
            model_version_files.update_or_create_files()
            logger.debug("Updated '{}' Version {} for update".format(destination_folder, version_id))
            commit(repo, "Version {}".format(version_id), creator)
            logger.debug("Committed '{}' Version {}".format(destination_folder, version_id))
        else:
            logger.warning('Model version with Drupal ID {} does not have a model. Ignoring.'.format(drupal_model_id))


def get_or_create_repo(full_path: str) -> pygit2.Repository:
    if not os.path.exists(full_path):
        os.makedirs(full_path, exist_ok=True)
        repo = pygit2.init_repository(full_path, bare=True)
    else:
        repo = pygit2.discover_repository(full_path)
    return repo


def create_signature(creator: User):
    return pygit2.Signature(creator.get_full_name(), creator.email)


def move_content(repo, model_version):
    pass


def commit(repo: pygit2.Repository, message, creator: User):
    signature = create_signature(creator)

    index = repo.index
    index.read()
    index.add_all()

    index.write()
    tree = index.write_tree()

    today = datetime.date.today().strftime("%B %d, %Y")

    parents = [repo.head.get_object().hex]

    sha = repo.create_commit('refs/head/master',
                             signature,
                             signature,
                             message,
                             tree,
                             parents)

    return sha
