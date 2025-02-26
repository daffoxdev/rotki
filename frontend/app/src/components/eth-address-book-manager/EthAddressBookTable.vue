<template>
  <div>
    <data-table
      :items="filteredData"
      :headers="tableHeaders"
      :loading="loading"
    >
      <template #item.actions="{ item }">
        <row-actions
          :disabled="loading"
          :delete-tooltip="tc('eth_address_book.actions.delete.tooltip')"
          :edit-tooltip="tc('eth_address_book.actions.edit.tooltip')"
          @delete-click="pending = item"
          @edit-click="edit(item)"
        />
      </template>
    </data-table>
    <confirm-dialog
      :title="tc('eth_address_book.actions.delete.dialog.title')"
      :message="tc('eth_address_book.actions.delete.dialog.message')"
      :display="showConfirmation"
      @confirm="deleteAddressBook"
      @cancel="dismiss"
    />
  </div>
</template>
<script lang="ts">
import { NotificationPayload, Severity } from '@rotki/common/lib/messages';
import { get, set } from '@vueuse/core';
import {
  computed,
  defineComponent,
  onBeforeMount,
  PropType,
  Ref,
  ref,
  toRefs
} from 'vue';
import { useI18n } from 'vue-i18n-composable';
import { DataTableHeader } from 'vuetify';
import RowActions from '@/components/helper/RowActions.vue';
import i18n from '@/i18n';
import { useEthNamesStore } from '@/store/balances/ethereum-names';
import {
  EthAddressBookLocation,
  EthNamesEntries,
  EthNamesEntry
} from '@/store/balances/types';
import { useNotifications } from '@/store/notifications';
import { Nullable } from '@/types';

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: i18n.t('common.address').toString(),
    value: 'address'
  },
  {
    text: i18n.t('common.name').toString(),
    value: 'name'
  },
  {
    text: '',
    value: 'actions'
  }
]);

const addressBookDeletion = (location: Ref<EthAddressBookLocation>) => {
  const pending = ref<Nullable<EthNamesEntry>>(null);
  const showConfirmation = computed(() => !!get(pending));

  const dismiss = () => {
    set(pending, null);
  };

  const { tc } = useI18n();
  const { notify } = useNotifications();
  const { deleteEthAddressBook } = useEthNamesStore();

  const deleteAddressBook = async () => {
    if (!get(pending)) return;
    const address = get(pending)!.address;
    set(pending, null);

    try {
      await deleteEthAddressBook(get(location), [address]);
    } catch (e: any) {
      const notification: NotificationPayload = {
        title: tc('eth_address_book.actions.delete.error.title'),
        message: tc('eth_address_book.actions.delete.error.description', 0, {
          message: e.message
        }).toString(),
        display: true,
        severity: Severity.ERROR
      };
      notify(notification);
    }
  };

  return {
    showConfirmation,
    pending,
    deleteAddressBook,
    dismiss
  };
};

export default defineComponent({
  name: 'EthAddressBookTable',
  components: { RowActions },
  props: {
    location: {
      required: true,
      type: String as PropType<EthAddressBookLocation>
    },
    search: { required: false, type: String, default: '' }
  },
  emits: ['edit'],
  setup(props, { emit }) {
    const { location, search } = toRefs(props);
    const ethNamesStore = useEthNamesStore();
    const { fetchEthAddressBook } = ethNamesStore;
    const { ethAddressBook } = toRefs(ethNamesStore);
    const loading = ref<boolean>(false);

    const { tc } = useI18n();

    const data = computed<EthNamesEntries>(() => {
      return get(ethAddressBook)[get(location)];
    });

    const filteredData = computed<EthNamesEntries>(() => {
      if (!get(search)) return get(data);
      const keyword = get(search).toLowerCase();
      return get(data).filter(
        item =>
          item.address.includes(keyword) ||
          item.name.toLowerCase().includes(keyword)
      );
    });

    const edit = (item: EthNamesEntry) => {
      emit('edit', item);
    };

    onBeforeMount(async () => {
      set(loading, true);
      await fetchEthAddressBook(get(location));
      set(loading, false);
    });

    return {
      loading,
      tableHeaders,
      filteredData,
      ...addressBookDeletion(location),
      edit,
      tc
    };
  }
});
</script>
