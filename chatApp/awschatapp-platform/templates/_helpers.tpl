{{- define "awschatapp.fullname" -}}
{{- printf "%s-api" .Release.Name }}
{{- end }}

{{- define "awschatapp.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
app.kubernetes.io/name: chat-api
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "awschatapp.selectorLabels" -}}
app.kubernetes.io/name: chat-api
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
