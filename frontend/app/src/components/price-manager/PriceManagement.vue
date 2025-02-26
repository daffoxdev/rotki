<template>
  <v-container>
    <v-row justify="space-between" align="center" no-gutters>
      <v-col>
        <card-title>{{ tc('price_management.title') }}</card-title>
      </v-col>
    </v-row>
    <card class="mt-8">
      <template #title>{{ tc('price_management.filter_title') }}</template>
      <v-row>
        <v-col cols="12" md="6">
          <asset-select
            v-model="filter.fromAsset"
            outlined
            :label="tc('price_management.from_asset')"
            clearable
          />
        </v-col>
        <v-col cols="12" md="6">
          <asset-select
            v-model="filter.toAsset"
            outlined
            :label="tc('price_management.to_asset')"
            clearable
          />
        </v-col>
      </v-row>
    </card>
    <price-table
      class="mt-12"
      :filter="filter"
      :refresh="refresh"
      @edit="openForm($event)"
      @refreshed="refresh = false"
    >
      <v-btn absolute fab top right color="primary" @click="openForm()">
        <v-icon> mdi-plus </v-icon>
      </v-btn>
    </price-table>
    <big-dialog
      :display="showForm"
      :title="
        editMode
          ? tc('price_management.dialog.edit_title')
          : tc('price_management.dialog.add_title')
      "
      :action-disabled="!valid"
      @confirm="managePrice(priceForm, editMode)"
      @cancel="hideForm()"
    >
      <price-form
        v-model="priceForm"
        :edit="editMode"
        @valid="valid = $event"
      />
    </big-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { get, set } from '@vueuse/core';
import { onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n-composable';
import BigDialog from '@/components/dialogs/BigDialog.vue';
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import PriceForm from '@/components/price-manager/PriceForm.vue';
import PriceTable from '@/components/price-manager/PriceTable.vue';
import { useRoute, useRouter } from '@/composables/common';
import {
  HistoricalPrice,
  HistoricalPriceFormPayload
} from '@/services/assets/types';
import { api } from '@/services/rotkehlchen-api';
import { useMainStore } from '@/store/main';
import { Nullable } from '@/types';

const emptyPrice: () => HistoricalPriceFormPayload = () => ({
  fromAsset: '',
  toAsset: '',
  price: '0',
  timestamp: 0
});

const refresh = ref(false);
const priceForm = ref<HistoricalPriceFormPayload>(emptyPrice());
const showForm = ref(false);
const filter = reactive<{
  fromAsset: Nullable<string>;
  toAsset: Nullable<string>;
}>({
  fromAsset: null,
  toAsset: null
});
const valid = ref(false);
const editMode = ref(false);

const { setMessage } = useMainStore();
const router = useRouter();
const route = useRoute();
const { tc } = useI18n();

const openForm = (hPrice: HistoricalPrice | null = null) => {
  set(editMode, !!hPrice);
  if (hPrice) {
    set(priceForm, {
      ...hPrice,
      price: hPrice.price.toFixed() ?? ''
    });
  } else {
    const emptyPriceObj = emptyPrice();
    set(priceForm, {
      ...emptyPriceObj,
      fromAsset: filter.fromAsset ?? '',
      toAsset: filter.toAsset ?? ''
    });
  }
  set(showForm, true);
};

const hideForm = function () {
  set(showForm, false);
  set(priceForm, emptyPrice());
};

const managePrice = async (
  price: HistoricalPriceFormPayload,
  edit: boolean
) => {
  try {
    if (edit) {
      await api.assets.editHistoricalPrice(price);
    } else {
      await api.assets.addHistoricalPrice(price);
    }

    set(showForm, false);
    if (!get(refresh)) {
      set(refresh, true);
    }
  } catch (e: any) {
    const values = { message: e.message };
    const title = edit
      ? tc('price_management.edit.error.title')
      : tc('price_management.add.error.title');
    const description = edit
      ? tc('price_management.edit.error.description', 0, values)
      : tc('price_management.add.error.description', 0, values);
    setMessage({
      title,
      description,
      success: false
    });
  }
};

onMounted(() => {
  const query = get(route).query;

  if (query.add) {
    openForm();
    router.replace({ query: {} });
  }
});
</script>
