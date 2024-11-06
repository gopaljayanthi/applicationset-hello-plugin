# ApplicationSet Hello Plugin

This is an example ApplicationSet plugin generator.

## Testing

First, install Argo CD on your cluster.

Second, install the plugin's manifests. The manifests assume that Argo CD is installed in the `argocd` namespace and
that you want to install the plugin Deployment in the `applicationset-hello-plugin` namespace.

clone this repo, go to the base folder and run following command

```bash
kubectl apply -k .
```
  
create a secret in the applicationset-hello-plugin namespace  
kubectl -n applicationset-hello-plugin create secret generic github-token-secret --from-literal=GITHUB_TOKEN=yourgithubtoken

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: multicm-myplugin
spec:
  goTemplate: true
  goTemplateOptions: ["missingkey=error"]
  generators:
    - plugin:
        configMapRef:
          name: applicationset-hello-plugin
        input:
          parameters:
            repo: "gopaljayanthi/forjpmc"
            branch: "master"
            folder: "pluginfiles"
        requeueAfterSeconds: 60
  template:
    metadata:
      name: "multicm-myplugin"
      annotations:
        example.from.plugin.output: "{{ .contents }}"
    spec:
      project: default
      source:
        repoURL: https://github.com/gopaljayanthi/forjpmc.git
        path: multicm-plugin-helm
        targetRevision: master
      destination:
        server: https://kubernetes.default.svc
        namespace: default
  templatePatch: |
    spec:
      source:
        helm:
          parameters:
          {{- if .contents }}
          {{- range $fileName, $fileContents := .contents }}
            - name: 'configMapFiles.{{ $fileName | replace "." "\\." }}'
              value: '{{ $fileContents }}'
          {{- end }}
            - name: "name"
              value: '{{.name}}'
          {{- end }}
```
