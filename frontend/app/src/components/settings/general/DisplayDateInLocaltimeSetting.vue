<template>
  <settings-option
    #default="{ error, success, update }"
    setting="displayDateInLocaltime"
    :error-message="
      $tc('general_settings.validation.display_date_in_localtime.error')
    "
  >
    <v-switch
      v-model="displayDateInLocaltime"
      class="general-settings__fields__display-date-in-localtime mb-4 mt-0"
      color="primary"
      :label="$t('general_settings.labels.display_date_in_localtime')"
      :success-messages="success"
      :error-messages="error"
      @change="update"
    />
  </settings-option>
</template>

<script setup lang="ts">
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { onMounted, ref } from 'vue';
import { useGeneralSettingsStore } from '@/store/settings/general';

const displayDateInLocaltime = ref<boolean>(true);
const { displayDateInLocaltime: enabled } = storeToRefs(
  useGeneralSettingsStore()
);

onMounted(() => {
  set(displayDateInLocaltime, get(enabled));
});
</script>
