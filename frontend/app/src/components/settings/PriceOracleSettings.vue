<template>
  <setting-category>
    <template #title>
      {{ $t('price_oracle_settings.title') }}
    </template>
    <template #subtitle>
      {{ $t('price_oracle_settings.subtitle') }}
    </template>

    <v-row>
      <v-col cols="12" md="6">
        <settings-option
          #default="{ error, success, update }"
          setting="currentPriceOracles"
          @finished="resetCurrentPriceOracles"
        >
          <price-oracle-selection
            :value="currentOracles"
            :all-items="availableCurrentOracles"
            :status="{ error, success }"
            @input="update"
          >
            <template #title>
              {{ $t('price_oracle_settings.current_prices') }}
            </template>
          </price-oracle-selection>
        </settings-option>
      </v-col>

      <v-col cols="12" md="6">
        <settings-option
          #default="{ error, success, update }"
          setting="historicalPriceOracles"
          @finished="resetHistoricalPriceOracles"
        >
          <price-oracle-selection
            :value="historicOracles"
            :all-items="availableHistoricOracles"
            :status="{ error, success }"
            @input="update"
          >
            <template #title>
              {{ $t('price_oracle_settings.historic_prices') }}
            </template>
          </price-oracle-selection>
        </settings-option>
      </v-col>
    </v-row>
    <v-row>
      <v-col class="text-caption">
        {{ $t('price_oracle_selection.hint') }}
      </v-col>
    </v-row>
  </setting-category>
</template>

<script setup lang="ts">
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { onMounted, ref } from 'vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import PriceOracleSelection from '@/components/settings/PriceOracleSelection.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';
import { useGeneralSettingsStore } from '@/store/settings/general';

const baseAvailableOracles = ['cryptocompare', 'coingecko'];
const availableCurrentOracles: string[] = [
  ...baseAvailableOracles,
  'uniswapv2',
  'uniswapv3',
  'saddle'
];
const availableHistoricOracles = [...baseAvailableOracles, 'manual'];

const currentOracles = ref<string[]>([]);
const historicOracles = ref<string[]>([]);

const { currentPriceOracles, historicalPriceOracles } = storeToRefs(
  useGeneralSettingsStore()
);

const resetCurrentPriceOracles = () => {
  set(currentOracles, get(currentPriceOracles));
};

const resetHistoricalPriceOracles = () => {
  set(historicOracles, get(historicalPriceOracles));
};

onMounted(() => {
  resetCurrentPriceOracles();
  resetHistoricalPriceOracles();
});
</script>
