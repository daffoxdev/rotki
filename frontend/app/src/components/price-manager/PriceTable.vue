<template>
  <card outlined-body>
    <template #title>{{ tc('price_table.title') }}</template>
    <slot />
    <data-table
      :items="prices"
      :headers="headers"
      :loading="loading"
      sort-by="timestamp"
    >
      <template #item.fromAsset="{ item }">
        <asset-details :asset="item.fromAsset" />
      </template>
      <template #item.toAsset="{ item }">
        <asset-details :asset="item.toAsset" />
      </template>
      <template #item.timestamp="{ item }">
        <date-display :timestamp="item.timestamp" />
      </template>
      <template #item.price="{ item }">
        <amount-display :value="item.price" />
      </template>
      <template #item.wasWorth>{{ tc('price_table.was_worth') }}</template>
      <template #item.on>{{ tc('price_table.on') }}</template>
      <template #item.actions="{ item }">
        <row-actions
          :disabled="loading"
          :delete-tooltip="tc('price_table.actions.delete.tooltip')"
          :edit-tooltip="tc('price_table.actions.edit.tooltip')"
          @delete-click="pending = item"
          @edit-click="$emit('edit', item)"
        />
      </template>
    </data-table>
    <confirm-dialog
      :title="tc('price_table.delete.dialog.title')"
      :message="tc('price_table.delete.dialog.message')"
      :display="showConfirmation"
      @confirm="deletePrice"
      @cancel="dismiss"
    />
  </card>
</template>

<script setup lang="ts">
import { NotificationPayload, Severity } from '@rotki/common/lib/messages';
import { get, set } from '@vueuse/core';
import { computed, onMounted, PropType, ref, toRef, watch } from 'vue';
import { useI18n } from 'vue-i18n-composable';
import { DataTableHeader } from 'vuetify';
import RowActions from '@/components/helper/RowActions.vue';
import {
  HistoricalPrice,
  HistoricalPricePayload
} from '@/services/assets/types';
import { api } from '@/services/rotkehlchen-api';
import { useNotifications } from '@/store/notifications';
import { Nullable } from '@/types';
import { nonNullProperties } from '@/utils/data';

const props = defineProps({
  filter: {
    type: Object as PropType<HistoricalPricePayload>,
    required: true
  },
  refresh: {
    type: Boolean,
    required: false,
    default: false
  }
});

const emit = defineEmits(['edit', 'refreshed']);

const filter = toRef(props, 'filter');

const prices = ref<HistoricalPrice[]>([]);
const loading = ref(false);
const pending = ref<Nullable<HistoricalPrice>>(null);
const showConfirmation = computed(() => !!get(pending));

const { notify } = useNotifications();
const { tc } = useI18n();

const headers = computed<DataTableHeader[]>(() => [
  {
    text: tc('price_table.headers.from_asset'),
    value: 'fromAsset'
  },
  {
    text: '',
    value: 'wasWorth'
  },
  {
    text: tc('common.price'),
    value: 'price'
  },
  {
    text: tc('price_table.headers.to_asset'),
    value: 'toAsset'
  },
  {
    text: '',
    value: 'on'
  },
  {
    text: tc('common.datetime'),
    value: 'timestamp'
  },
  {
    text: '',
    value: 'actions'
  }
]);

const dismiss = () => {
  set(pending, null);
};

const deletePrice = async () => {
  const { price, ...payload } = get(pending)!;
  set(pending, null);
  try {
    await api.assets.deleteHistoricalPrice(payload);
    await refresh();
  } catch (e: any) {
    const notification: NotificationPayload = {
      title: tc('price_table.delete.failure.title'),
      message: tc('price_table.delete.failure.message', 0, {
        message: e.message
      }),
      display: true,
      severity: Severity.ERROR
    };
    notify(notification);
  }
};

const fetchPrices = async (payload?: Partial<HistoricalPricePayload>) => {
  set(loading, true);
  try {
    set(prices, await api.assets.historicalPrices(payload));
  } catch (e: any) {
    const notification: NotificationPayload = {
      title: tc('price_table.fetch.failure.title'),
      message: tc('price_table.fetch.failure.message', 0, {
        message: e.message
      }),
      display: true,
      severity: Severity.ERROR
    };
    notify(notification);
  } finally {
    set(loading, false);
  }
};

const refresh = async () => {
  await fetchPrices(get(filter));
};

watch(props.filter, async payload => {
  await fetchPrices(nonNullProperties(payload));
});

watch(
  () => props.refresh,
  async refresh => {
    if (!refresh) {
      return;
    }
    await fetchPrices();
    emit('refreshed');
  }
);

onMounted(fetchPrices);
</script>
