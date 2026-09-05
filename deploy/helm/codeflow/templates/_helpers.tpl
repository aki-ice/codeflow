{{/*
通用命名
*/}}
{{- define "codeflow.name" -}}
{{- .Release.Name }}-{{ .Chart.Name }}
{{- end -}}

{{- define "codeflow.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/*
完整镜像地址：registry 前缀 + 镜像名 + tag
*/}}
{{- define "codeflow.image" -}}
{{- if .global.imageRegistry }}{{ .global.imageRegistry }}/{{ .image }}{{ else }}{{ .image }}{{ end }}:{{ .global.imageTag }}
{{- end -}}
