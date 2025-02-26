<template>
  <fragment>
    <div class="d-flex overflow-hidden">
      <sync-indicator />
      <global-search v-if="!xsOnly" />
      <back-button :can-navigate-back="canNavigateBack" />
    </div>
    <v-spacer />
    <div class="d-flex overflow-hidden fill-height align-center">
      <v-btn v-if="isDevelopment && !xsOnly" to="/playground" icon>
        <v-icon>mdi-crane</v-icon>
      </v-btn>
      <app-update-indicator />
      <user-notes-indicator
        :visible="showNotesSidebar"
        @visible:update="showNotesSidebar = $event"
      />
      <pinned-indicator
        :visible="showPinned"
        @visible:update="showPinned = $event"
      />
      <theme-control v-if="!xsOnly" :dark-mode-enabled="darkModeEnabled" />
      <notification-indicator
        :visible="showNotificationBar"
        class="app__app-bar__button"
        @click="showNotificationBar = !showNotificationBar"
      />
      <currency-dropdown class="app__app-bar__button" />
      <privacy-mode-dropdown v-if="!xsOnly" class="app__app-bar__button" />
      <user-dropdown class="app__app-bar__button" />
      <help-indicator
        v-if="!xsOnly"
        :visible="showHelpBar"
        @visible:update="showHelpBar = $event"
      />
    </div>
  </fragment>
</template>

<script setup lang="ts">
import { get } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { computed, defineAsyncComponent } from 'vue';
import Fragment from '@/components/helper/Fragment';
import { useRoute, useTheme } from '@/composables/common';
import { useDarkMode } from '@/composables/session';
import { useAreaVisibilityStore } from '@/store/session/visibility';
import { checkIfDevelopment } from '@/utils/env-utils';

const isDevelopment = checkIfDevelopment();

const ThemeControl = defineAsyncComponent(
  () => import('@/components/premium/ThemeControl.vue')
);
const CurrencyDropdown = defineAsyncComponent(
  () => import('@/components/CurrencyDropdown.vue')
);
const AppUpdateIndicator = defineAsyncComponent(
  () => import('@/components/status/AppUpdateIndicator.vue')
);
const NotificationIndicator = defineAsyncComponent(
  () => import('@/components/status/NotificationIndicator.vue')
);
const SyncIndicator = defineAsyncComponent(
  () => import('@/components/status/sync/SyncIndicator.vue')
);
const PinnedIndicator = defineAsyncComponent(
  () => import('@/components/PinnedIndicator.vue')
);
const UserNotesIndicator = defineAsyncComponent(
  () => import('@/components/UserNotesIndicator.vue')
);
const BackButton = defineAsyncComponent(
  () => import('@/components/helper/BackButton.vue')
);
const GlobalSearch = defineAsyncComponent(
  () => import('@/components/GlobalSearch.vue')
);
const HelpIndicator = defineAsyncComponent(
  () => import('@/components/help/HelpIndicator.vue')
);
const UserDropdown = defineAsyncComponent(
  () => import('@/components/UserDropdown.vue')
);
const PrivacyModeDropdown = defineAsyncComponent(
  () => import('@/components/PrivacyModeDropdown.vue')
);

const { currentBreakpoint } = useTheme();
const xsOnly = computed(() => get(currentBreakpoint).xsOnly);

const { darkModeEnabled } = useDarkMode();
const { showPinned, showNotesSidebar, showNotificationBar, showHelpBar } =
  storeToRefs(useAreaVisibilityStore());

const route = useRoute();
const canNavigateBack = computed(() => {
  const canNavigateBack = get(route).meta?.canNavigateBack ?? false;
  return canNavigateBack && window.history.length > 1;
});
</script>
