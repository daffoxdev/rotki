<template>
  <tab-navigation :tab-contents="tabs" data-cy="accounts-balances-tab" />
</template>

<script setup lang="ts">
import { get } from '@vueuse/core';
import TabNavigation, {
  TabContent
} from '@/components/helper/TabNavigation.vue';
import { routesRef } from '@/router/routes';

const Routes = get(routesRef);

const tabs: TabContent[] = [
  Routes.ACCOUNTS_BALANCES_BLOCKCHAIN,
  Routes.ACCOUNTS_BALANCES_EXCHANGE,
  Routes.ACCOUNTS_BALANCES_MANUAL,
  Routes.ACCOUNTS_BALANCES_NON_FUNGIBLE
];
</script>
