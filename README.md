Flask application deployed on Amazon EKS with PostgreSQL database, Loki logging, and Grafana monitoring dashboards.

Prerequisites
AWS CLI configured with proper permissions

Docker installed and running

kubectl CLI tool

eksctl for EKS management

Helm v3 for package management

1. Build and Push Docker Image
Navigate to the application directory and build the container image:

# Build the Flask application image
docker build -t flask-eks-app:latest .

# Authenticate with Docker Hub
docker login

# Tag image with your Docker Hub username
docker tag flask-eks-app:latest masiam/flask-eks-app:latest


2. Create EKS Cluster
Set up a new Amazon EKS cluster with managed node groups:
 Create EKS cluster with managed nodes
eksctl create cluster \
  --name flask-monitoring-cluster \
  --version 1.28 \
  --region us-west-2 \
  --nodegroup-name worker-nodes \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 4 \
  --managed

# Configure kubectl to use the new cluster
aws eks update-kubeconfig --region us-west-2 --name flask-monitoring-cluster

3. Install Required EKS Add-ons
Install the EBS CSI driver for persistent volume support:
Create IAM service account for EBS CSI driver
eksctl create iamserviceaccount \
  --name ebs-csi-controller-sa \
  --namespace kube-system \
  --cluster flask-monitoring-cluster \
  --role-name EKS_EBS_CSI_DriverRole \
  --role-only \
  --attach-policy-arn arn:aws:iam::aws:policy/service-role/Amazon_EBS_CSI_DriverPolicy \
  --approve

# Install EBS CSI driver add-on
aws eks create-addon \
  --cluster-name flask-monitoring-cluster \
  --addon-name aws-ebs-csi-driver \
  --service-account-role-arn arn:aws:iam::${AWS_ACCOUNT_ID}:role/EKS_EBS_CSI_DriverRole \
  --region us-west-2

Note: i have already exported my AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)


Install AWS Load Balancer Controller for external access: I have used Load Balancer as service for my flask app to hit url externally.

curl -o iam_policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.6.0/docs/install/iam_policy.json

aws iam create-policy \
    --policy-name AWSLoadBalancerControllerIAMPolicy \
    --policy-document file://iam_policy.json

# Create service account with IAM role
eksctl create iamserviceaccount \
  --cluster=flask-monitoring-cluster \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --role-name AmazonEKSLoadBalancerControllerRole \
  --attach-policy-arn=arn:aws:iam::${AWS_ACCOUNT_ID}:policy/AWSLoadBalancerControllerIAMPolicy \
  --approve

# Install AWS Load Balancer Controller via Helm
helm repo add eks https://aws.github.io/eks-charts
helm repo update

helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=flask-monitoring-cluster \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller


4. Deploy Application Components

kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/postgres-secret.yaml
kubectl apply -f k8s/postgres-pvc.yaml
kubectl apply -f k8s/postgres-statefulset.yaml
kubectl apply -f k8s/postgres-service.yaml
kubectl apply -f k8s/flask-configmap.yaml
kubectl apply -f k8s/flask-deployment.yaml
kubectl apply -f k8s/flask-service.yaml
kubectl apply -f k8s/pinger-deployment.yaml
kubectl apply -f k8s/ingress.yaml

5. Install Monitoring Stack

helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Install Loki stack for log collection
helm install loki grafana/loki-stack \
  --namespace=monitoring \
  --create-namespace \
  -f helm-values/loki-values.yaml

Deploy Grafana for visualization:

helm install grafana grafana/grafana \
  --namespace=monitoring \
  -f helm-values/grafana-values.yaml

6. Get Application URL and Test Endpoints

FLASK_URL=$(kubectl get service flask-service -n flask-app -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "Flask Application URL: http://$FLASK_URL"

# Test endpoint
curl -s http://$FLASK_URL/serviceup | jq

curl -s http://$FLASK_URL/user/1 | jq

curl -s http://$FLASK_URL/user?id=1 | jq

curl -s http://$FLASK_URL/user/999 | jq


7. Access Grafana Dashboard and configure
Set up port forwarding and access the monitoring interface:
open it via node port http://workernode:node port in 30k range


# Retrieve Grafana admin credentials
 "Username: admin"
  pasword: .....


Add Loki Data Source:

Navigate to Configuration → Data Sources
Click "Add data source"
Select "Loki"
Set URL to: http://loki.monitoring.svc.cluster.local:3100 setting an correct url is imp
Click "Save & Test"

Import Dashboard:
Copy the dashboard JSON from grafana/dashboard.json

after this step you will able to see dashboar



