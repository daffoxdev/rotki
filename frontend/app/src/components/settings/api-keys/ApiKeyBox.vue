<template>
  <v-row no-gutters class="mt-8">
    <v-col cols="12">
      <v-sheet outlined rounded>
        <slot />
      </v-sheet>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

export default defineComponent({
  name: 'ApiKeyBox'
});
</script>
