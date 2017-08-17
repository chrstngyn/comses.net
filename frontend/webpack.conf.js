const path = require('path');
const stringify = require('stringify-object')

const webpack = require('webpack');
const {
    createConfig, match, entryPoint, setOutput, addPlugins,
    customConfig, defineConstants, env, sourceMaps
} = require('webpack-blocks');
const { url } = require('@webpack-blocks/assets');
const typescript = require('@webpack-blocks/typescript');
const sass = require('@webpack-blocks/sass');
const extractText = require('@webpack-blocks/extract-text');
const BundleTracker = require('webpack-bundle-tracker');
const CompressionWebpackPlugin = require('compression-webpack-plugin');
const { TsConfigPathsPlugin } = require('awesome-typescript-loader');


module.exports = createConfig([
    entryPoint({
        codebases: './src/pages/codebase',
        jobs: './src/pages/job',
        events: './src/pages/event',
        profiles: './src/pages/profile',
        job_list: './src/pages/job/list.ts',
        event_list: './src/pages/event/list.ts',
        codebase_list: './src/pages/codebase/list.ts',
        event_calendar: './src/pages/event/calendar.ts',
        styles: './src/styles/index.scss',
        vendors: './src/vendors.ts'
    }),
    setOutput({
        path: '/shared/webpack',
        filename: 'js/[name].[chunkhash].js',
        publicPath: '/static/'
    }),
    customConfig({
        resolve: {
            modules: [
                'src',
                'node_modules'
            ],
            alias: {
                'vue$': 'vue/dist/vue.common.js',
                'api': path.resolve(__dirname, 'src/api'),
                'pages': path.resolve(__dirname, 'src/pages'),
                'assets': path.resolve(__dirname, 'src/assets'),
                'store': path.resolve(__dirname, 'src/store'),
                'components': path.resolve(__dirname, 'src/components')
            }
        }
    }),
    typescript(),
    match('*.scss', { exclude: path.resolve('node_modules') }, [
        sass(),
        extractText('[name]-[contenthash:8].css')
    ]),
    match(/\.(png|jpe?g|gif|svg)(\?.*)?$/, [
        url({
            limit: 10000,
            name: 'img/[name].[hash:7].[ext]'
        })
    ]),
    match(/\.(woff2?|eot|ttf|otf)(\?.*)?$/, [
        url({
            limit: 50000,
            mimetype: 'application/font-woff',
            name: 'fonts/[name].[hash:7].[ext]'
        })
    ]),
    addPlugins([
        new webpack.ProvidePlugin({
            $: "jquery",
            jQuery: "jquery",
            "window.jQuery": "jquery",
            Popper: ['popper.js', 'default'],
            Alert: "exports-loader?Alert!bootstrap/js/dist/alert",
            Button: "exports-loader?Button!bootstrap/js/dist/button",
            Carousel: "exports-loader?Carousel!bootstrap/js/dist/carousel",
            Collapse: "exports-loader?Collapse!bootstrap/js/dist/collapse",
            Dropdown: "exports-loader?Dropdown!bootstrap/js/dist/dropdown",
            Modal: "exports-loader?Modal!bootstrap/js/dist/modal",
            Popover: "exports-loader?Popover!bootstrap/js/dist/popover",
            Scrollspy: "exports-loader?Scrollspy!bootstrap/js/dist/scrollspy",
            Tab: "exports-loader?Tab!bootstrap/js/dist/tab",
            Tooltip: "exports-loader?Tooltip!bootstrap/js/dist/tooltip",
            Util: "exports-loader?Util!bootstrap/js/dist/util",
        }),
        // split vendor js into its own file
        new webpack.optimize.CommonsChunkPlugin({
            name: 'vendors'
        }),
        // extract webpack runtime and module manifest to its own file in order to
        // prevent vendor hash from being updated whenever app bundle is updated
        new webpack.optimize.CommonsChunkPlugin({
            name: 'manifest',
            chunks: ['vendors']
        }),
        new BundleTracker({ path: '/shared/webpack', filename: './webpack-stats.json' })
    ]),
    sourceMaps('source-map'),
    defineConstants({
        'process.env.NODE_ENV': process.env.NODE_ENV,
        '__BASE_URL__': process.env.BASE_URL
    }),
    env('development', [

    ]),
    env('production', [
        addPlugins([
            new webpack.optimize.UglifyJsPlugin({
                compress: {
                    warnings: false
                }
            }),
            new webpack.LoaderOptionsPlugin({ minimize: true }),
            new webpack.optimize.OccurrenceOrderPlugin(),
            new CompressionWebpackPlugin({
                asset: '[path].gz[query]',
                algorithm: 'gzip',
                test: new RegExp(
                    '\\.(' +
                    ['js', 'css'].join('|') +
                    ')$'
                ),
                threshold: 10240,
                minRatio: 0.8
            })
        ])
    ])
]);

console.log(stringify({ resolve: module.exports.resolve, module: module.exports.module }))