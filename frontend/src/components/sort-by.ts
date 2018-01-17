import {Component, Prop} from 'vue-property-decorator'
import Vue from 'vue'
import * as queryString from 'query-string'

@Component({
    // language=Vue
    template: `<form class='form-inline py-2 mx-1'>
        <div class='form-group'>
            <label for='ordering'><b class='title'>Sort By: </b></label>
            <select v-model="selectedOptionValue" class='form-control form-control mx-2'>
                <option v-for='sortOption in sortOptions' :value='sortOption.value' :selected="sortOption.value === selectedOptionValue">
                {{ sortOption.label }}
                </option>
            </select>
        </div>
        <div class='form-check form-check-inline mx-2'>
            <input v-model='sortByAscDesc' class='form-check-input' value='asc' type='radio' name='sort_type' id='sort_ascending' checked>
            <label class='form-check-label' for='sort_ascending'>Sort ascending</label>
        </div>
        <div class='form-check form-check-inline mx-2'>
            <input v-model='sortByAscDesc' class='form-check-input' value='desc' type='radio' name='sort_type' id='sort_descending'>
            <label class='form-check-label' for='sort_descending'>Sort descending</label>
        </div>
        <button type='button' @click="updateSortBy" class='btn btn-secondary'>Apply</button>
    </form>`
})
export class SortBy extends Vue {
    @Prop()
    sortOptions: Array<{label:string, value: string}>;

    selectedOptionValue: string;

    sortByAscDesc: string;

    created() {
        const queryParams = queryString.parse(window.location.search);
        const orderingQueryParam = queryParams['ordering'] || 'last_modified';
        if (orderingQueryParam.startsWith('-')) {
            this.selectedOptionValue = orderingQueryParam.slice(1);
            this.sortByAscDesc = "desc";
        }
        else {
            this.selectedOptionValue = orderingQueryParam;
            this.sortByAscDesc = "asc";
        }
    }

    get orderingParameter() {
        if (this.sortByAscDesc === "desc") {
            return "-" + this.selectedOptionValue;
        }
        return this.selectedOptionValue;
    }

    updateSortBy() {
        const queryParams = queryString.parse(window.location.search);
        queryParams['ordering'] = this.orderingParameter;
        window.location.search = queryString.stringify(queryParams);
    }

}
