<template>
  <div>
    <div class="d-flex align-center" :class="$style.wrapper">
      <div class="my-2" :class="$style.preview">
        <template v-if="imageUrl">
          <video
            v-if="isVideo(imageUrl)"
            width="100%"
            height="100%"
            aspect-ratio="1"
            :src="imageUrl"
          />
          <v-img
            v-else
            :src="imageUrl"
            width="100%"
            height="100%"
            contain
            aspect-ratio="1"
          />
        </template>
      </div>
      <div class="ml-4" :class="$style.name">
        {{ name }}
      </div>
    </div>
  </div>
</template>
<script lang="ts">
import { get } from '@vueuse/core';
import { computed, defineComponent, toRefs } from 'vue';
import { NonFungibleBalance } from '@/store/balances/types';
import { getNftBalance, isVideo } from '@/utils/nft';

export default defineComponent({
  name: 'NftDetails',
  props: {
    identifier: {
      required: true,
      type: String
    }
  },
  setup(props) {
    const { identifier } = toRefs(props);

    const balanceData = computed<NonFungibleBalance | null>(() => {
      return getNftBalance(get(identifier));
    });

    const imageUrl = computed<string | null>(() => {
      return get(balanceData)?.imageUrl ?? '/assets/images/placeholder.svg';
    });

    const name = computed<string>(() => {
      return get(balanceData)?.name ?? get(identifier);
    });

    return {
      imageUrl,
      name,
      isVideo
    };
  }
});
</script>

<style module lang="scss">
.wrapper {
  overflow: hidden;
}

.preview {
  background: #f5f5f5;
  width: 50px;
  height: 50px;
  max-width: 50px;
  min-width: 50px;
}

.name {
  flex: 1;
}
</style>
