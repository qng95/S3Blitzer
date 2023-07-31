#!/usr/bin/env bash

eks_region=$(terraform output -raw region)
eks_cluster_name=$(terraform output -raw cluster_name)

aws eks --region "${eks_region}" update-kubeconfig --name "${eks_cluster_name}" --kubeconfig ./../../.secrets/kubeconfig-aws
