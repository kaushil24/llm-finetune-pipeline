# Some gotchas 

1. To pull from private container registery, you need to add k8s secret
2. How to expose IP for k8s clusture
   1. Remember to specify --namespace param while listing services
   2. Also this is a good way to demonstrate and understand concepts like services, deployments etc
   - The approach is to use LoadBalancer type. And then use `kubectl get services -n airflpw` to list ExternalIP
3. The whole airflow logging/permission denied error
4. Write about PVC for logging
5. How to add prom and grafana (https://github.com/iam-veeramalla/prometheus-Grafana-Zero-to-Hero/blob/main/Installation/Grafana/helm.md) but also add kubectl get svc and change the last command to LoadBalancer

- Interesting things learnt
  - busybox
  - increase limit and request in k8s for a container. Also what does the m in cpu unit mean?


# connect to k8s cluster
1. az account set --subscription 3753e0a8-6838-4371-9801-4006b95be84f
2. az aks get-credentials --resource-group customllm --name customllmk8s
3. kubectl create namespace airflpw 
4. kubectl config set-context --current --namespace=airflpw 
   1. kubectl config view --minify | grep namespace:
5. add secret: kubectl create secret docker-registry img-pull-sec-3 --namespace airflpw --docker-server=customllmreg.azurecr.io --docker-username=88b8f18d-2496-4ef8-bd93-ca21c2f8baf0 --docker-password=5.t8Q~wuPg1AiyRlvQnMjxeXmGUtLNJkHypY0cKE
6. helm upgrade --recreate-pods  --install airflow . --create-namespace  --namespace airflpw --values values.yaml
   1. Few small steps: change imagePullSecret in helm values
   2. 
7. add prometheus:
   1. This is a 2 step process. 1st is to add prometheus repo to helm
   2. install on the cluster: helm install prometheus prometheus-community/prometheus --namespace airflpw   
