# More Information: <https://cloud.google.com/resource-manager/reference/rest>

from typing import Generator, List, Tuple

from . import exceptions
from .base import AccountManagerMixin, DiscoveryMixin, GoogleCloudPilotAPI, PolicyType, ResourceType


class ResourceManager(AccountManagerMixin, DiscoveryMixin, GoogleCloudPilotAPI):
    def __init__(self, **kwargs):
        super().__init__(
            serviceName="cloudresourcemanager",
            version="v1",
            cache_discovery=False,
            **kwargs,
        )

    def get_policy(self, project_id: str = None, version: int = 1) -> PolicyType:
        return self._execute(
            method=self.client.projects().getIamPolicy,
            resource=project_id or self.project_id,
            body={"options": {"requestedPolicyVersion": version}},
        )

    def set_policy(self, policy: PolicyType, project_id: str = None) -> PolicyType:
        if not policy["bindings"]:
            raise exceptions.NotAllowed("Too dangerous to set policy with empty bindings")

        return self._execute(
            method=self.client.projects().setIamPolicy,
            resource=project_id or self.project_id,
            body={"policy": policy, "updateMask": "bindings"},
        )

    async def add_member(self, email: str, role: str, project_id: str = None) -> PolicyType:
        policy = self.get_policy(project_id=project_id)
        changed_policy = self._bind_email_to_policy(email=email, role=role, policy=policy)
        return self.set_policy(policy=changed_policy, project_id=project_id)

    async def remove_member(self, email: str, role: str, project_id: str = None) -> PolicyType:
        policy = self.get_policy(project_id=project_id)
        changed_policy = self._unbind_email_from_policy(email=email, role=role, policy=policy)
        return self.set_policy(policy=changed_policy, project_id=project_id)

    def get_project(self, project_id: str) -> ResourceType:
        return self._execute(
            method=self.client.projects().get,
            projectId=project_id or self.project_id,
        )

    async def allow_impersonation(self, email: str, project_id: str = None) -> PolicyType:
        return await self.add_member(
            email=email,
            role="roles/iam.serviceAccountTokenCreator",
            project_id=project_id,
        )


class ServiceAgent:
    agents = {
        "AI Platform Custom Code Service Agent": ("gcp-sa-aiplatform-cc.iam.gserviceaccount.com", None),
        "AI Platform Service Agent": ("gcp-sa-aiplatform.iam.gserviceaccount.com", None),
        "ASM Mesh Data Plane Service Account": (
            "gcp-sa-meshdataplane.iam.gserviceaccount.com",
            "roles/meshdataplane.serviceAgent",
        ),
        "Anthos Audit Service Account": ("gcp-sa-anthosaudit.iam.gserviceaccount.com", None),
        "Anthos Config Management Service Account": (
            "gcp-sa-anthosconfigmanagement.iam.gserviceaccount.com",
            "roles/anthosconfigmanagement.serviceAgent",
        ),
        "Anthos Identity Service Account": (
            "gcp-sa-anthosidentityservice.iam.gserviceaccount.com",
            "roles/anthosidentityservice.serviceAgent",
        ),
        "Anthos Service Account": ("gcp-sa-anthos.iam.gserviceaccount.com", "roles/anthos.serviceAgent"),
        "Anthos Service Mesh Service Account": ("gcp-sa-servicemesh.iam.gserviceaccount.com", None),
        "Apigee Service Agent": ("gcp-sa-apigee.iam.gserviceaccount.com", "roles/apigee.serviceAgent"),
        "App Engine Flexible Environment Service Agent": (
            "gae-api-prod.google.com.iam.gserviceaccount.com",
            "roles/appengineflex.serviceAgent",
        ),
        "Artifact Registry Service Agent": (
            "gcp-sa-artifactregistry.iam.gserviceaccount.com",
            "roles/artifactregistry.serviceAgent",
        ),
        "AssuredWorkloads Service Account": ("gcp-sa-assuredworkloads.iam.gserviceaccount.com", None),
        "AutoML Recommendations Service Account": (
            "gcp-sa-recommendationengine.iam.gserviceaccount.com",
            "roles/automlrecommendations.serviceAgent",
        ),
        "AutoML Service Agent": ("gcp-sa-automl.iam.gserviceaccount.com", "roles/automl.serviceAgent"),
        "BigQuery Connection Service Agent": (
            "gcp-sa-bigqueryconnection.iam.gserviceaccount.com",
            "roles/bigqueryconnection.serviceAgent",
        ),
        "BigQuery Data Transfer Service Agent": (
            "gcp-sa-bigquerydatatransfer.iam.gserviceaccount.com",
            "roles/bigquerydatatransfer.serviceAgent",
        ),
        "BigQuery Omni Service Agent": ("gcp-sa-prod-bigqueryomni.iam.gserviceaccount.com", None),
        "Binary Authorization Service Agent": (
            "gcp-sa-binaryauthorization.iam.gserviceaccount.com",
            "roles/binaryauthorization.serviceAgent",
        ),
        "Cloud AI Platform Notebooks Service Account": (
            "gcp-sa-notebooks.iam.gserviceaccount.com",
            "roles/notebooks.serviceAgent",
        ),
        "Cloud API Gateway Management Plane Service Account": ("gcp-sa-apigateway-mgmt.iam.gserviceaccount.com", None),
        "Cloud API Gateway Service Account": ("gcp-sa-apigateway.iam.gserviceaccount.com", None),
        "Cloud Asset Service Agent": ("gcp-sa-cloudasset.iam.gserviceaccount.com", "roles/cloudasset.serviceAgent"),
        "Cloud Bigtable Service Agent": ("gcp-sa-bigtable.iam.gserviceaccount.com", None),
        "Cloud Build Service Agent": ("gcp-sa-cloudbuild.iam.gserviceaccount.com", "roles/cloudbuild.serviceAgent"),
        "Cloud Composer Service Agent": (
            "cloudcomposer-accounts.iam.gserviceaccount.com",
            "roles/composer.serviceAgent",
        ),
        "Cloud Data Fusion Service Account": (
            "gcp-sa-datafusion.iam.gserviceaccount.com",
            "roles/datafusion.serviceAgent",
        ),
        "Cloud Database Migration Service Account": ("gcp-sa-datamigration.iam.gserviceaccount.com", None),
        "Cloud Dataflow Service Account": (
            "dataflow-service-producer-prod.iam.gserviceaccount.com",
            "roles/dataflow.serviceAgent",
        ),
        "Cloud Endpoints Service Agent": ("gcp-sa-endpoints.iam.gserviceaccount.com", "roles/endpoints.serviceAgent"),
        "Cloud File Storage Service Account": ("cloud-filer.iam.gserviceaccount.com", "roles/file.serviceAgent"),
        "Cloud Healthcare Service Agent": (
            "gcp-sa-healthcare.iam.gserviceaccount.com",
            "roles/healthcare.serviceAgent",
        ),
        "Cloud IoT Core Service Agent": ("gcp-sa-cloudiot.iam.gserviceaccount.com", "roles/cloudiot.serviceAgent"),
        "Cloud KMS Service Agent": ("gcp-sa-cloudkms.iam.gserviceaccount.com", "roles/cloudkms.serviceAgent"),
        "Cloud Life Sciences Service Agent": (
            "gcp-sa-lifesciences.iam.gserviceaccount.com",
            "roles/lifesciences.serviceAgent",
        ),
        "Cloud Logging Service Account": ("gcp-sa-logging.iam.gserviceaccount.com", None),
        "Cloud Managed Identities Service Agent": (
            "gcp-sa-mi.iam.gserviceaccount.com",
            "roles/managedidentities.serviceAgent",
        ),
        "Cloud Memorystore Memcache Service Agent": (
            "cloud-memcache-sa.iam.gserviceaccount.com",
            "roles/memcache.serviceAgent",
        ),
        "Cloud Memorystore Redis Service Agent": ("cloud-redis.iam.gserviceaccount.com", "roles/redis.serviceAgent"),
        "Cloud Network Management Service Account": (
            "gcp-sa-networkmanagement.iam.gserviceaccount.com",
            "roles/networkmanagement.serviceAgent",
        ),
        "Cloud Pub/Sub Service Account": ("gcp-sa-pubsub.iam.gserviceaccount.com", None),
        "Cloud SQL Service Account": ("gcp-sa-cloud-sql.iam.gserviceaccount.com", "roles/cloudsql.serviceAgent"),
        "Cloud Scheduler Service Account": (
            "gcp-sa-cloudscheduler.iam.gserviceaccount.com",
            "roles/cloudscheduler.serviceAgent",
        ),
        "Cloud Security Command Center Notification Service Account": (
            "gcp-sa-scc-notification.iam.gserviceaccount.com",
            "roles/securitycenter.notificationServiceAgent",
        ),
        "Cloud Source Repositories Service Agent": (
            "sourcerepo-service-accounts.iam.gserviceaccount.com",
            "roles/sourcerepo.serviceAgent",
        ),
        "Cloud Spanner Production Service Account": ("gcp-sa-spanner.iam.gserviceaccount.com", None),
        "Cloud Storage for Firebase Service Agent": (
            "gcp-sa-firebasestorage.iam.gserviceaccount.com",
            "roles/firebasestorage.serviceAgent",
        ),
        "Cloud Tasks Service Account": ("gcp-sa-cloudtasks.iam.gserviceaccount.com", "roles/cloudtasks.serviceAgent"),
        "Cloud Trace Service Account": ("gcp-sa-cloud-trace.iam.gserviceaccount.com", None),
        "Cloud Translation Service Agent": (
            "gcp-sa-translation.iam.gserviceaccount.com",
            "roles/cloudtranslate.serviceAgent",
        ),
        "Cloud VM Migration Service Account": ("gcp-sa-vmmigration.iam.gserviceaccount.com", None),
        "Cloud Web Security Scanner Service Agent": (
            "gcp-sa-websecurityscanner.iam.gserviceaccount.com",
            "roles/websecurityscanner.serviceAgent",
        ),
        "Cloud Workflows Service Agent": ("gcp-sa-workflows.iam.gserviceaccount.com", "roles/workflows.serviceAgent"),
        "Compute Engine Service Agent": ("compute-system.iam.gserviceaccount.com", "roles/compute.serviceAgent"),
        "Compute Scanning Service Agent": (
            "gcp-sa-computescanning.iam.gserviceaccount.com",
            "roles/computescanning.serviceAgent",
        ),
        "Container Analysis Service Agent": (
            "container-analysis.iam.gserviceaccount.com",
            "roles/containeranalysis.ServiceAgent",
        ),
        "Container Scanning Service Agent": (
            "gcp-sa-containerscanning.iam.gserviceaccount.com",
            "roles/containerscanning.ServiceAgent",
        ),
        "Container Threat Detection Service Agent": (
            "gcp-sa-ktd-control.iam.gserviceaccount.com",
            "roles/containerthreatdetection.serviceAgent",
        ),
        "Data Labeling Service Account": (
            "gcp-sa-datalabeling.iam.gserviceaccount.com",
            "roles/datalabeling.serviceAgent",
        ),
        "Data Studio Service Account": ("gcp-sa-datastudio.iam.gserviceaccount.com", "roles/datastudio.serviceAgent"),
        "Dataproc Metastore Service Account": ("gcp-sa-metastore.iam.gserviceaccount.com", None),
        "Dialogflow Service Agent": ("gcp-sa-dialogflow.iam.gserviceaccount.com", "roles/dialogflow.serviceAgent"),
        "DocumentAI Core Service Agent": (
            "gcp-sa-prod-dai-core.iam.gserviceaccount.com",
            "roles/documentaicore.serviceAgent",
        ),
        "Endpoints Consumer Portal Service Agent": (
            "endpoints-portal.iam.gserviceaccount.com",
            "roles/endpointsportal.serviceAgent",
        ),
        "Eventarc Service Agent": ("gcp-sa-eventarc.iam.gserviceaccount.com", "roles/eventarc.serviceAgent"),
        "External Key Management Service Service Account": ("gcp-sa-ekms.iam.gserviceaccount.com", None),
        "Firebase Extensions Service Agent": (
            "gcp-sa-firebasemods.iam.gserviceaccount.com",
            "roles/firebasemods.serviceAgent",
        ),
        "Firebase Rules Service Agent": ("firebase-rules.iam.gserviceaccount.com", None),
        "Firewall Insights Service Account": (
            "gcp-sa-firewallinsights.iam.gserviceaccount.com",
            "roles/firewallinsights.serviceAgent",
        ),
        "GKE Hub API Service Account": ("gcp-sa-gkehub.iam.gserviceaccount.com", "roles/gkehub.serviceAgent"),
        "Game Services Agent": ("gcp-sa-gameservices.iam.gserviceaccount.com", "roles/gameservices.serviceAgent"),
        "Google Cloud Dataproc Service Agent": (
            "dataproc-accounts.iam.gserviceaccount.com",
            "roles/dataproc.serviceAgent",
        ),
        "Google Cloud Functions Service Agent": (
            "gcf-admin-robot.iam.gserviceaccount.com",
            "roles/cloudfunctions.serviceAgent",
        ),
        "Google Cloud ML Engine Service Agent": (
            "cloud-ml.google.com.iam.gserviceaccount.com",
            "roles/ml.serviceAgent",
        ),
        "Google Cloud OS Config Service Agent": (
            "gcp-sa-osconfig.iam.gserviceaccount.com",
            "roles/osconfig.serviceAgent",
        ),
        "Google Cloud Run Service Agent": ("serverless-robot-prod.iam.gserviceaccount.com", "roles/run.serviceAgent"),
        "Google Container Registry Service Agent": (
            "containerregistry.iam.gserviceaccount.com",
            "roles/containerregistry.ServiceAgent",
        ),
        "Google Genomics Service Agent": (
            "genomics-api.google.com.iam.gserviceaccount.com",
            "roles/genomics.serviceAgent",
        ),
        "Kubernetes Engine Service Agent": (
            "container-engine-robot.iam.gserviceaccount.com",
            "roles/container.serviceAgent",
        ),
        "Mesh Config Service Account": ("gcp-sa-meshconfig.iam.gserviceaccount.com", "roles/meshconfig.serviceAgent"),
        "Monitoring Notification Service Account": (
            "gcp-sa-monitoring-notification.iam.gserviceaccount.com",
            "roles/monitoring.notificationServiceAgent",
        ),
        "Multi Cluster Ingress Service Account": (
            "gcp-sa-multiclusteringress.iam.gserviceaccount.com",
            "roles/multiclusteringress.serviceAgent",
        ),
        "Multi cluster metering Service Account": (
            "gcp-sa-mcmetering.iam.gserviceaccount.com",
            "roles/multiclustermetering.serviceAgent",
        ),
        "Private CA Service Account": ("gcp-sa-privateca.iam.gserviceaccount.com", None),
        "Remote Build Execution Service Agent": (
            "remotebuildexecution.iam.gserviceaccount.com",
            "roles/remotebuildexecution.serviceAgent",
        ),
        "Retail Service Account": ("gcp-sa-retail.iam.gserviceaccount.com", "roles/retail.serviceAgent"),
        "Secret Manager Service Account": ("gcp-sa-secretmanager.iam.gserviceaccount.com", None),
        "Serverless VPC Access Service Agent": (
            "gcp-sa-vpcaccess.iam.gserviceaccount.com",
            "roles/vpcaccess.serviceAgent",
        ),
        "Service Consumer Management Service Agent": ("service-consumer-management.iam.gserviceaccount.com", None),
        "Service Directory Service Account": ("gcp-sa-servicedirectory.iam.gserviceaccount.com", None),
        "Service Networking Service Agent": (
            "service-networking.iam.gserviceaccount.com",
            "roles/servicenetworking.serviceAgent",
        ),
        "TPU Service Agent": ("cloud-tpu.iam.gserviceaccount.com", "roles/tpu.serviceAgent"),
        "TPU Service Agent (v2)": ("gcp-sa-tpu.iam.gserviceaccount.com", "roles/cloudtpu.serviceAgent"),
        "Transcoder Service Account": ("gcp-sa-transcoder.iam.gserviceaccount.com", None),
    }

    _suffixes = ["Service Agent", "Agent", "Service Account"]

    @classmethod
    def get_available_agents(cls) -> Generator[str, None, None]:
        for agent in cls.agents:
            name = agent
            for suffix in cls._suffixes:
                name = name.replace(suffix, "")
            yield name

    @classmethod
    def _load_from_tsv(cls, filepath: str):
        # Load this <https://cloud.google.com/iam/docs/service-agents> table
        data = {}
        with open(filepath, "r", encoding="utf-8") as file:
            for line in file.readlines()[1:]:
                name, domain, role = line.strip().split("\t")
                if "roles/" not in role:
                    role_name = None
                else:
                    role_name = role.replace("(", "").replace(")", "")
                data[name] = (domain, role_name)
        return data

    @classmethod
    def _find(cls, service_name: str) -> Tuple[str, str]:
        candidates = [f"{service_name} {suffix}" for suffix in cls._suffixes]

        for candidate in candidates:
            try:
                return cls.agents[candidate]
            except KeyError:
                continue

        raise exceptions.NotFound(f"Service {service_name} not found")

    @classmethod
    def get_email(cls, service_name: str, project_id: str) -> str:
        domain, _ = cls._find(service_name=service_name)
        project_number = cls.get_project_number(project_id=project_id)
        return f"service-{project_number}@{domain}"

    @classmethod
    def get_role(cls, service_name: str) -> str:
        _, role = cls._find(service_name=service_name)
        return role

    @classmethod
    def get_project_number(cls, project_id: str) -> int:
        # TODO: cache this
        project = ResourceManager().get_project(project_id=project_id)
        return project["projectNumber"]

    @classmethod
    async def restore(cls, services: List[str], project_id: str) -> None:
        rm = ResourceManager()  # pylint: disable=invalid-name
        for service_name in services:
            email = ServiceAgent.get_email(service_name=service_name, project_id=project_id)
            role = ServiceAgent.get_role(service_name=service_name)
            if role:
                try:
                    await rm.add_member(email=email, role=role)
                    print(f"[O] {service_name}")
                except exceptions.ValidationError:
                    print(f"[X] {service_name}")

    @classmethod
    def get_compute_service_account(cls, project_id: str) -> str:
        project_number = cls.get_project_number(project_id=project_id)
        return f"{project_number}-compute@developer.gserviceaccount.com"

    @classmethod
    def get_cloud_build_service_account(cls, project_id: str = None) -> str:
        project_number = cls.get_project_number(project_id=project_id)
        return f"{project_number}@cloudbuild.gserviceaccount.com"


__all__ = (
    "ResourceManager",
    "ServiceAgent",
)
