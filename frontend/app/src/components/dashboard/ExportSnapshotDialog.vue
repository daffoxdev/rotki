<template>
  <v-dialog :value="value" max-width="600" @input="updateVisibility">
    <card>
      <template #title>
        {{ $t('dashboard.snapshot.export_database_snapshot') }}
      </template>
      <template #subtitle>
        {{ $t('dashboard.snapshot.subtitle') }}
      </template>
      <div class="mb-n2">
        <div>
          <div>{{ $t('common.datetime') }}:</div>
          <div>
            <date-display class="font-weight-bold" :timestamp="timestamp" />
          </div>
        </div>
        <div class="pt-2">
          <div>{{ $t('common.balance') }}:</div>
          <div>
            <amount-display
              :value="formattedSelectedBalance"
              :fiat-currency="currency"
              class="font-weight-bold"
            />
          </div>
        </div>
      </div>
      <template #buttons>
        <v-btn color="primary" @click="editMode = true">
          <v-icon class="mr-2">mdi-pencil-outline</v-icon>
          {{ $t('common.actions.edit') }}
        </v-btn>
        <v-btn color="error" @click="deleteSnapshotConfirmationDialog = true">
          <v-icon class="mr-2">mdi-delete-outline</v-icon>
          {{ $t('common.actions.delete') }}
        </v-btn>
        <v-spacer />
        <v-btn color="primary" @click="exportSnapshot">
          <v-icon class="mr-2">mdi-download</v-icon>
          {{ $t('common.actions.download') }}
        </v-btn>
      </template>
    </card>
    <confirm-dialog
      v-if="deleteSnapshotConfirmationDialog"
      display
      :title="$tc('dashboard.snapshot.delete.dialog.title')"
      :message="$tc('dashboard.snapshot.delete.dialog.message')"
      @cancel="deleteSnapshotConfirmationDialog = false"
      @confirm="deleteSnapshot"
    />
    <edit-snapshot-dialog
      v-if="editMode"
      :timestamp="timestamp"
      @close="editMode = false"
      @finish="finish"
    />
  </v-dialog>
</template>
<script lang="ts">
import { BigNumber } from '@rotki/common';
import { Message } from '@rotki/common/lib/messages';
import { get, set } from '@vueuse/core';
import dayjs from 'dayjs';
import { storeToRefs } from 'pinia';
import { computed, defineComponent, ref, toRefs } from 'vue';
import EditSnapshotDialog from '@/components/dashboard/EditSnapshotDialog.vue';
import { interop } from '@/electron-interop';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { useMainStore } from '@/store/main';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useStatisticsStore } from '@/store/statistics';
import { bigNumberifyFromRef } from '@/utils/bignumbers';
import { downloadFileByUrl } from '@/utils/download';

export default defineComponent({
  name: 'ExportSnapshotDialog',
  components: { EditSnapshotDialog },
  props: {
    value: { required: false, type: Boolean, default: false },
    timestamp: { required: false, type: Number, default: 0 },
    balance: { required: false, type: Number, default: 0 }
  },
  emits: ['input'],
  setup(props, { emit }) {
    const { timestamp, balance } = toRefs(props);
    const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
    const editMode = ref<boolean>(false);

    const deleteSnapshotConfirmationDialog = ref<boolean>(false);

    const updateVisibility = (visible: boolean) => {
      emit('input', visible);
    };

    const formattedSelectedBalance = computed<BigNumber | null>(() => {
      if (get(balance)) {
        return get(bigNumberifyFromRef(balance));
      }

      return null;
    });

    const downloadSnapshot = async () => {
      const resp = await api.downloadSnapshot(get(timestamp));

      const blob = new Blob([resp.data], { type: 'application/zip' });
      const url = window.URL.createObjectURL(blob);

      const date = dayjs(get(timestamp) * 1000).format('YYYYDDMMHHmmss');
      const fileName = `${date}-snapshot.zip`;

      downloadFileByUrl(url, fileName);

      updateVisibility(false);
    };

    const { setMessage } = useMainStore();

    const exportSnapshotCSV = async () => {
      let message: Message | null = null;

      try {
        if (interop.isPackaged && api.defaultBackend) {
          const path = await interop.openDirectory(
            i18n.t('dashboard.snapshot.select_directory').toString()
          );

          if (!path) {
            return;
          }

          const success = await api.exportSnapshotCSV({
            path,
            timestamp: get(timestamp)
          });

          message = {
            title: i18n
              .t('dashboard.snapshot.download.message.title')
              .toString(),
            description: success
              ? i18n.t('dashboard.snapshot.download.message.success').toString()
              : i18n
                  .t('dashboard.snapshot.download.message.failure')
                  .toString(),
            success
          };

          updateVisibility(false);
        } else {
          await downloadSnapshot();
        }
      } catch (e: any) {
        message = {
          title: i18n.t('dashboard.snapshot.download.message.title').toString(),
          description: e.message,
          success: false
        };
      }

      if (message) {
        setMessage(message);
      }
    };

    const exportSnapshot = () => {
      if (interop.isPackaged) {
        exportSnapshotCSV();
      } else {
        downloadSnapshot();
      }
    };

    const { fetchNetValue } = useStatisticsStore();

    const deleteSnapshot = async () => {
      let message: Message | null;

      try {
        const success = await api.deleteSnapshot({
          timestamp: get(timestamp)
        });

        message = {
          title: i18n.t('dashboard.snapshot.delete.message.title').toString(),
          description: success
            ? i18n.t('dashboard.snapshot.delete.message.success').toString()
            : i18n.t('dashboard.snapshot.delete.message.failure').toString(),
          success
        };

        updateVisibility(false);
        fetchNetValue();
      } catch (e: any) {
        message = {
          title: i18n.t('dashboard.snapshot.download.message.title').toString(),
          description: e.message,
          success: false
        };
      }

      set(deleteSnapshotConfirmationDialog, false);

      setMessage(message);
    };

    const finish = () => {
      updateVisibility(false);
      set(editMode, false);
    };

    return {
      editMode,
      currency: currencySymbol,
      formattedSelectedBalance,
      deleteSnapshotConfirmationDialog,
      updateVisibility,
      exportSnapshot,
      deleteSnapshot,
      finish
    };
  }
});
</script>
