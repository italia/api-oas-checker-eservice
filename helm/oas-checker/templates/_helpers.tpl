{{/*
Expand the name of the chart.
*/}}
{{- define "oas-checker.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "oas-checker.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "oas-checker.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "oas-checker.labels" -}}
helm.sh/chart: {{ include "oas-checker.chart" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: oas-checker
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
{{- end }}

{{/*
E-Service selector labels
*/}}
{{- define "oas-checker.eservice.selectorLabels" -}}
app.kubernetes.io/name: {{ include "oas-checker.name" . }}-eservice
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: eservice
{{- end }}

{{/*
E-Service labels
*/}}
{{- define "oas-checker.eservice.labels" -}}
{{ include "oas-checker.labels" . }}
{{ include "oas-checker.eservice.selectorLabels" . }}
{{- end }}

{{/*
Worker selector labels
*/}}
{{- define "oas-checker.worker.selectorLabels" -}}
app.kubernetes.io/name: {{ include "oas-checker.name" . }}-worker
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: worker
{{- end }}

{{/*
Worker labels
*/}}
{{- define "oas-checker.worker.labels" -}}
{{ include "oas-checker.labels" . }}
{{ include "oas-checker.worker.selectorLabels" . }}
{{- end }}

{{/*
GovWay selector labels
*/}}
{{- define "oas-checker.govway.selectorLabels" -}}
app.kubernetes.io/name: {{ include "oas-checker.name" . }}-govway
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: govway
{{- end }}

{{/*
GovWay labels
*/}}
{{- define "oas-checker.govway.labels" -}}
{{ include "oas-checker.labels" . }}
{{ include "oas-checker.govway.selectorLabels" . }}
{{- end }}

{{/*
E-Service image
*/}}
{{- define "oas-checker.eservice.image" -}}
{{- $tag := default .Chart.AppVersion .Values.eservice.image.tag -}}
{{- printf "%s:%s" .Values.eservice.image.repository $tag }}
{{- end }}

{{/*
Worker image
*/}}
{{- define "oas-checker.worker.image" -}}
{{- $tag := default .Chart.AppVersion .Values.worker.image.tag -}}
{{- printf "%s:%s" .Values.worker.image.repository $tag }}
{{- end }}

{{/*
Secret name (supports existingSecret)
*/}}
{{- define "oas-checker.secretName" -}}
{{- if .Values.secrets.existingSecret }}
{{- .Values.secrets.existingSecret }}
{{- else }}
{{- include "oas-checker.fullname" . }}
{{- end }}
{{- end }}

{{/*
ConfigMap name
*/}}
{{- define "oas-checker.configMapName" -}}
{{- include "oas-checker.fullname" . }}
{{- end }}

{{/*
Database URL - builds from Bitnami subchart or external database config
*/}}
{{- define "oas-checker.databaseUrl" -}}
{{- if .Values.postgresql.enabled }}
{{- $host := printf "%s-postgresql" (include "oas-checker.fullname" .) -}}
{{- $port := "5432" -}}
{{- $user := .Values.postgresql.auth.username -}}
{{- $pass := .Values.postgresql.auth.password -}}
{{- $db := .Values.postgresql.auth.database -}}
{{- printf "postgresql://%s:%s@%s:%s/%s" $user $pass $host $port $db }}
{{- else if .Values.externalDatabase.url }}
{{- .Values.externalDatabase.url }}
{{- else }}
{{- printf "postgresql://%s:%s@%s:%v/%s" .Values.externalDatabase.user .Values.externalDatabase.password .Values.externalDatabase.host (.Values.externalDatabase.port | toString) .Values.externalDatabase.database }}
{{- end }}
{{- end }}

{{/*
Function URL - resolves based on worker mode
*/}}
{{- define "oas-checker.functionUrl" -}}
{{- if eq .Values.worker.mode "external" }}
{{- .Values.worker.externalUrl }}
{{- else if eq .Values.worker.mode "knative" }}
{{- printf "http://%s-worker.%s.svc.cluster.local/api/validate" (include "oas-checker.fullname" .) .Release.Namespace }}
{{- else }}
{{- printf "http://%s-worker:%v/api/validate" (include "oas-checker.fullname" .) (.Values.worker.service.port | toString) }}
{{- end }}
{{- end }}

{{/*
Callback URL for the worker to call back the eservice
*/}}
{{- define "oas-checker.callbackUrl" -}}
{{- printf "http://%s-eservice:%v" (include "oas-checker.fullname" .) (.Values.eservice.service.port | toString) }}
{{- end }}

{{/*
Service account name
*/}}
{{- define "oas-checker.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "oas-checker.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
PVC name for ruleset cache
*/}}
{{- define "oas-checker.rulesetCachePvcName" -}}
{{- printf "%s-ruleset-cache" (include "oas-checker.fullname" .) }}
{{- end }}
