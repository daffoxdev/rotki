<template>
  <v-container>
    <generate
      v-show="!isRunning && !reportError.message"
      @generate="generate($event)"
      @export-data="exportData($event)"
      @import-data="importDataDialog = true"
    />
    <error-screen
      v-if="!isRunning && reportError.message"
      class="mt-12"
      :message="reportError.message"
      :error="reportError.error"
      :title="tc('profit_loss_report.error.title')"
      :subtitle="tc('profit_loss_report.error.subtitle')"
    >
      <template #bottom>
        <v-btn text class="mt-2" @click="clearError()">
          {{ tc('common.actions.close') }}
        </v-btn>
      </template>
    </error-screen>
    <reports-table v-show="!isRunning && !reportError.message" class="mt-8" />
    <progress-screen v-if="isRunning" :progress="progress">
      <template #message>
        <div v-if="processingState" class="medium text-h6 mb-4">
          {{ processingState }}
        </div>
        {{ tc('profit_loss_report.loading_message') }}
      </template>
      {{ tc('profit_loss_report.loading_hint') }}
    </progress-screen>
    <v-dialog v-model="importDataDialog" max-width="600">
      <card>
        <template #title>
          {{ tc('profit_loss_reports.debug.import_data_dialog.title') }}
        </template>
        <div>
          <div class="py-2">
            <file-upload
              ref="reportDebugDataUploader"
              source="json"
              file-filter=".json"
              @selected="reportDebugData = $event"
            />
          </div>
          <div class="mt-2 d-flex justify-end">
            <v-btn class="mr-4" @click="importDataDialog = false">
              {{ tc('common.actions.cancel') }}
            </v-btn>
            <v-btn
              color="primary"
              :disabled="!reportDebugData"
              :loading="importDataLoading"
              @click="importData"
            >
              {{ tc('common.actions.import') }}
            </v-btn>
          </div>
        </div>
      </card>
    </v-dialog>
  </v-container>
</template>

<script lang="ts">
import { Message } from '@rotki/common/lib/messages';
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { computed, defineComponent, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n-composable';
import ErrorScreen from '@/components/error/ErrorScreen.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import FileUpload from '@/components/import/FileUpload.vue';
import Generate from '@/components/profitloss/Generate.vue';
import ReportsTable from '@/components/profitloss/ReportsTable.vue';
import { useRoute, useRouter } from '@/composables/common';
import { interop } from '@/electron-interop';
import { Routes } from '@/router/routes';
import { api } from '@/services/rotkehlchen-api';
import { useMainStore } from '@/store/main';
import { useReports } from '@/store/reports';
import { useAreaVisibilityStore } from '@/store/session/visibility';
import { useTasks } from '@/store/tasks';
import { showError, showMessage } from '@/store/utils';
import {
  ProfitLossReportDebugPayload,
  ProfitLossReportPeriod
} from '@/types/reports';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { downloadFileByUrl } from '@/utils/download';

export default defineComponent({
  name: 'ProfitLossReports',
  components: {
    FileUpload,
    ErrorScreen,
    ReportsTable,
    ProgressScreen,
    Generate
  },
  setup() {
    const { isTaskRunning } = useTasks();
    const reportsStore = useReports();
    const { reportError } = storeToRefs(reportsStore);
    const { generateReport, clearError, exportReportData } = reportsStore;
    const isRunning = isTaskRunning(TaskType.TRADE_HISTORY);
    const importDataDialog = ref<boolean>(false);
    const reportDebugData = ref<File | null>(null);
    const importDataLoading = ref<boolean>(false);
    const reportDebugDataUploader = ref<any>(null);

    const router = useRouter();
    const route = useRoute();

    const { tc } = useI18n();

    onMounted(() => {
      const query = get(route).query;
      if (query.regenerate) {
        const start: string = (query.start as string) || '';
        const end: string = (query.end as string) || '';

        if (start && end) {
          const period = {
            start: parseInt(start),
            end: parseInt(end)
          };

          generate(period);
        }

        router.replace({ query: {} });
      }
    });

    const { pinned } = storeToRefs(useAreaVisibilityStore());

    const generate = async (period: ProfitLossReportPeriod) => {
      if (get(pinned)?.name === 'report-actionable-card') {
        set(pinned, null);
      }

      const reportId = await generateReport(period);
      if (reportId > 0) {
        router.push({
          path: Routes.PROFIT_LOSS_REPORT.route.replace(
            ':id',
            reportId.toString()
          ),
          query: {
            openReportActionable: 'true'
          }
        });
      }
    };

    const { setMessage } = useMainStore();

    const exportData = async ({ start, end }: ProfitLossReportPeriod) => {
      let payload: ProfitLossReportDebugPayload = {
        fromTimestamp: start,
        toTimestamp: end
      };

      let message: Message | null = null;

      try {
        const isLocal = interop.appSession;
        if (isLocal) {
          const directoryPath =
            (await interop.openDirectory(
              tc('profit_loss_reports.debug.select_directory')
            )) || '';
          if (!directoryPath) return;
          payload['directoryPath'] = directoryPath;
        }

        const result = await exportReportData(payload);

        if (isLocal) {
          message = {
            title: tc('profit_loss_reports.debug.export_message.title'),
            description: result
              ? tc('profit_loss_reports.debug.export_message.success')
              : tc('profit_loss_reports.debug.export_message.failure'),
            success: !!result
          };
        } else {
          const file = new Blob([JSON.stringify(result, null, 2)], {
            type: 'text/json'
          });
          const link = window.URL.createObjectURL(file);
          downloadFileByUrl(link, 'pnl_debug.json');
        }
      } catch (e: any) {
        message = {
          title: tc('profit_loss_reports.debug.export_message.title'),
          description: e.message,
          success: false
        };
      }

      if (message) {
        setMessage(message);
      }
    };

    const importData = async () => {
      if (!get(reportDebugData)) return;
      set(importDataLoading, true);

      let success = false;
      let message = '';

      const { awaitTask } = useTasks();
      const taskType = TaskType.IMPORT_PNL_REPORT_DATA;

      try {
        const { taskId } = interop.appSession
          ? await api.reports.importReportData(get(reportDebugData)!.path)
          : await api.reports.uploadReportData(get(reportDebugData)!);

        const { result } = await awaitTask<boolean, TaskMeta>(
          taskId,
          taskType,
          {
            title: tc('profit_loss_reports.debug.import_message.title'),
            numericKeys: []
          }
        );
        success = result;
      } catch (e: any) {
        message = e.message;
        success = false;
      }

      if (!success) {
        showError(
          tc('profit_loss_reports.debug.import_message.failure', 0, {
            message
          }),
          tc('profit_loss_reports.debug.import_message.title')
        );
      } else {
        showMessage(
          tc('profit_loss_reports.debug.import_message.success', 0, {
            message
          }),
          tc('profit_loss_reports.debug.import_message.title')
        );
      }

      set(importDataLoading, false);
      get(reportDebugDataUploader)?.removeFile();
      set(reportDebugData, null);
    };

    return {
      importDataDialog,
      importDataLoading,
      importData,
      reportDebugData,
      processingState: computed(() => reportsStore.processingState),
      progress: computed(() => reportsStore.progress),
      loaded: computed(() => reportsStore.loaded),
      isRunning,
      reportError,
      clearError,
      generate,
      exportData,
      tc
    };
  }
});
</script>
