<template>
  <settings-option
    #default="{ error, success, update }"
    setting="accountForAssetsMovements"
    :error-message="
      $tc('account_settings.messages.account_for_assets_movements')
    "
  >
    <v-switch
      v-model="accountForAssetsMovements"
      class="accounting-settings__account-for-assets-movements"
      :success-messages="success"
      :error-messages="error"
      :label="$tc('accounting_settings.labels.account_for_assets_movements')"
      color="primary"
      @change="update"
    />
  </settings-option>
</template>

<script setup lang="ts">
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { onMounted, ref } from 'vue';
import { useAccountingSettingsStore } from '@/store/settings/accounting';

const accountForAssetsMovements = ref(false);
const { accountForAssetsMovements: enabled } = storeToRefs(
  useAccountingSettingsStore()
);

onMounted(() => {
  set(accountForAssetsMovements, get(enabled));
});
</script>
