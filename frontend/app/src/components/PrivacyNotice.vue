<template>
  <div class="privacy-notice">
    <v-alert
      outlined
      dense
      color="primary"
      class="privacy-notice__message mb-0"
    >
      <div>{{ $t('privacy_notice.title') }}</div>
      <div>{{ $t('privacy_notice.message') }}</div>
    </v-alert>
  </div>
</template>
<script lang="ts">
import { defineComponent } from 'vue';

export default defineComponent({
  name: 'PrivacyNotice'
});
</script>
<style scoped lang="scss">
.privacy-notice {
  z-index: 4;

  &__message {
    text-align: center;
    font-size: 14px !important;
    background: #e0e0e0 !important;
  }
}
</style>
