<template>
  <v-tooltip v-if="canNavigateBack" open-delay="400" top>
    <template #activator="{ on, attrs }">
      <v-btn
        icon
        class="back-button__button"
        v-bind="attrs"
        v-on="on"
        @click="goBack()"
      >
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
    </template>
    <span>{{ $t('back_button.tooltip') }}</span>
  </v-tooltip>
  <div v-else class="back-button__placeholder" />
</template>
<script lang="ts">
import { defineComponent } from 'vue';
import { useRouter } from '@/composables/common';

export default defineComponent({
  name: 'BackButton',
  props: {
    canNavigateBack: { required: true, type: Boolean, default: false }
  },
  setup() {
    const router = useRouter();
    const goBack = () => {
      router.go(-1);
    };

    return {
      goBack
    };
  }
});
</script>
<style scoped lang="scss">
.back-button {
  &__button,
  &__placeholder {
    margin-left: 24px;
    width: 48px;
  }
}
</style>
