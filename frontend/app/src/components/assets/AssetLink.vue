<template>
  <v-btn :icon="icon" :text="text" @click="navigateToDetails">
    <slot />
  </v-btn>
</template>

<script lang="ts">
import { get } from '@vueuse/core';
import { defineComponent, toRefs } from 'vue';
import { useRouter } from '@/composables/common';
import { Routes } from '@/router/routes';

export default defineComponent({
  name: 'AssetLink',
  props: {
    asset: { required: true, type: String },
    icon: { required: false, default: false, type: Boolean },
    text: { required: false, default: false, type: Boolean }
  },
  setup(props) {
    const { asset } = toRefs(props);
    const router = useRouter();
    const navigateToDetails = () => {
      router.push({
        path: Routes.ASSETS.route.replace(':identifier', get(asset))
      });
    };

    return {
      navigateToDetails
    };
  }
});
</script>
