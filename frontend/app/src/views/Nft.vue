<template>
  <v-container>
    <module-not-active v-if="!isEnabled" :modules="modules" />
    <nft-gallery v-else :modules="modules" />
  </v-container>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import NftGallery from '@/components/nft/NftGallery.vue';
import { useModules } from '@/composables/session';
import { Module } from '@/types/modules';

export default defineComponent({
  name: 'Nft',
  components: { ModuleNotActive, NftGallery },
  setup() {
    const module = Module.NFTS;
    const { isModuleEnabled } = useModules();
    return {
      isEnabled: isModuleEnabled(module),
      modules: [module]
    };
  }
});
</script>
