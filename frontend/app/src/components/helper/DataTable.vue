<template>
  <v-data-table
    ref="tableRef"
    v-bind="$attrs"
    :must-sort="mustSort"
    :sort-desc="sortDesc"
    :items="items"
    :item-class="itemClass"
    :headers="headers"
    :expanded="expanded"
    :footer-props="footerProps"
    :items-per-page="itemsPerPage"
    :hide-default-footer="hideDefaultFooter"
    v-on="$listeners"
    @update:items-per-page="onItemsPerPageChange($event)"
    @update:page="scrollToTop"
  >
    <!-- Pass on all scoped slots -->
    <template
      v-for="slot in Object.keys($scopedSlots)"
      :slot="slot"
      slot-scope="scope"
    >
      <slot
        :name="slot"
        v-bind="
          // @ts-ignore
          scope
        "
      />
    </template>

    <!-- Pass on all named slots -->
    <slot v-for="slot in Object.keys($slots)" :slot="slot" :name="slot" />

    <template
      v-if="!hideDefaultFooter"
      #top="{ pagination, options, updateOptions }"
    >
      <v-data-footer
        v-bind="footerProps"
        :pagination="pagination"
        :options="options"
        @update:options="updateOptions"
      />
      <v-divider />
    </template>
  </v-data-table>
</template>

<script lang="ts">
import { get, useElementBounding } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { defineComponent, PropType, ref, toRefs } from 'vue';
import { DataTableHeader } from 'vuetify';
import { footerProps } from '@/config/datatable.common';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

export default defineComponent({
  name: 'DataTable',
  props: {
    sortDesc: { required: false, type: Boolean, default: true },
    mustSort: { required: false, type: Boolean, default: true },
    items: { required: true, type: Array },
    headers: { required: true, type: Array as PropType<DataTableHeader[]> },
    expanded: { required: false, type: Array, default: () => [] },
    itemClass: { required: false, type: [String, Function], default: () => '' },
    hideDefaultFooter: { required: false, type: Boolean, default: false },
    container: { required: false, type: HTMLDivElement, default: () => null }
  },
  setup(props) {
    let frontendSettingsStore = useFrontendSettingsStore();
    const { itemsPerPage } = storeToRefs(frontendSettingsStore);
    const { container } = toRefs(props);

    const tableRef = ref<any>(null);

    const onItemsPerPageChange = async (newValue: number) => {
      if (get(itemsPerPage) === newValue) return;

      await frontendSettingsStore.updateSetting({
        itemsPerPage: newValue
      });
    };

    const { top } = useElementBounding(tableRef);
    const { top: containerTop } = useElementBounding(container);

    const scrollToTop = () => {
      const wrapper = get(container) ?? document.body;
      const table = get(tableRef);

      if (!table || !wrapper) return;

      if (get(container)) {
        wrapper.scrollTop =
          get(top) +
          wrapper.scrollTop -
          get(containerTop) -
          table.$el.scrollTop;
      } else {
        wrapper.scrollTop = get(top) - 64;
      }
    };

    return {
      tableRef,
      itemsPerPage,
      footerProps,
      onItemsPerPageChange,
      scrollToTop
    };
  }
});
</script>

<style scoped lang="scss">
/* stylelint-disable selector-class-pattern,selector-nested-pattern,no-descending-specificity */

::v-deep {
  .v-data-table {
    &__expanded {
      &__content {
        background-color: var(--v-rotki-light-grey-base) !important;
        box-shadow: none !important;
      }
    }

    &--mobile {
      .v-data-table {
        &__wrapper {
          tbody {
            .v-data-table__expanded__content,
            .table-expand-container {
              height: auto !important;
              display: block;
            }
          }
        }
      }
    }
  }
}

.theme {
  &--dark {
    ::v-deep {
      .v-data-table {
        &__expanded {
          &__content {
            background-color: var(--v-dark-lighten1) !important;
          }
        }
      }
    }
  }
}
/* stylelint-enable selector-class-pattern,selector-nested-pattern,no-descending-specificity */
</style>
