<template>
  <stat-card :title="tc('loan_collateral.title')">
    <loan-row :title="tc('loan_collateral.locked_collateral')">
      <amount-display
        :asset-padding="assetPadding"
        :value="vault.collateral.amount"
        :asset="vault.collateral.asset"
      />
    </loan-row>
    <loan-row>
      <amount-display
        :asset-padding="assetPadding"
        :value="vault.collateral.usdValue"
        fiat-currency="USD"
      />
    </loan-row>
    <v-divider class="my-4" />
    <loan-row :title="tc('loan_collateral.current_ratio')" class="mb-2">
      <percentage-display :value="ratio" />
    </loan-row>
    <manage-watchers :vault="vault" />
  </stat-card>
</template>

<script lang="ts">
import { get } from '@vueuse/core';
import { computed, defineComponent, PropType, toRefs } from 'vue';
import { useI18n } from 'vue-i18n-composable';
import LoanRow from '@/components/defi/loan/LoanRow.vue';
import ManageWatchers from '@/components/defi/loan/loans/makerdao/ManageWatchers.vue';
import StatCard from '@/components/display/StatCard.vue';
import { MakerDAOVaultModel } from '@/store/defi/types';

export default defineComponent({
  name: 'MakerDaoVaultCollateral',
  components: { ManageWatchers, LoanRow, StatCard },
  props: {
    vault: {
      required: true,
      type: Object as PropType<MakerDAOVaultModel>
    }
  },
  setup(props) {
    const { vault } = toRefs(props);
    const { tc } = useI18n();
    const ratio = computed(() => {
      const value = get(vault);
      return value.collateralizationRatio ? value.collateralizationRatio : null;
    });
    return {
      ratio,
      assetPadding: 5,
      tc
    };
  }
});
</script>
