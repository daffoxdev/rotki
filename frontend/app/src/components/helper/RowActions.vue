<template>
  <div :class="$style.actions">
    <v-tooltip top>
      <template #activator="{ on, attrs }">
        <v-btn
          v-bind="attrs"
          icon
          :disabled="disabled"
          class="mx-1 actions__edit"
          data-cy="row-edit"
          v-on="on"
          @click="editClick"
        >
          <v-icon small> mdi-pencil-outline </v-icon>
        </v-btn>
      </template>
      <span>{{ editTooltip }}</span>
    </v-tooltip>
    <v-tooltip v-if="!noDelete" top>
      <template #activator="{ on, attrs }">
        <v-btn
          v-bind="attrs"
          icon
          :disabled="disabled || deleteDisabled"
          class="mx-1 actions__delete"
          data-cy="row-delete"
          v-on="on"
          @click="deleteClick"
        >
          <v-icon small> mdi-delete-outline </v-icon>
        </v-btn>
      </template>
      <span>{{ deleteTooltip }}</span>
    </v-tooltip>
    <slot />
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

export default defineComponent({
  name: 'RowAction',
  props: {
    disabled: { required: false, type: Boolean, default: false },
    deleteDisabled: { required: false, type: Boolean, default: false },
    editTooltip: { required: false, type: String, default: '' },
    deleteTooltip: { required: false, type: String, default: '' },
    noDelete: { required: false, type: Boolean, default: false }
  },
  emits: ['edit-click', 'delete-click'],
  setup(_, { emit }) {
    return {
      editClick: () => emit('edit-click'),
      deleteClick: () => emit('delete-click')
    };
  }
});
</script>

<style module lang="scss">
.actions {
  display: flex;
  flex-direction: row;
  flex-wrap: nowrap;
  align-items: center;
}
</style>
