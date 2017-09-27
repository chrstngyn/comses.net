import EditProfile, {schema} from './edit'
import * as _ from 'lodash'
import {__BASIC_AUTH_USERNAME__} from "../../__jest__/common"

describe('profile editing', () => {
    it('should allow updates', async () => {
        try {
            const vm = new EditProfile({ propsData: { _username: __BASIC_AUTH_USERNAME__}});
            await vm.initializeForm();
            expect((<any>vm).given_name).toBe('Test');

            (<any>vm).given_name = 'foo';
            await vm.createOrUpdate();
            await vm.initializeForm();
            expect((<any>vm).given_name).toBe('foo');

            (<any>vm).state.given_name = 'Test';
            await vm.createOrUpdate();
        } catch(e) {
            if (e.response) {
                console.log(e.response);
            }
            throw e;
        }
    });
});