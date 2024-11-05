# Enables the Cloud Run API for the project.
resource "google_project_service" "cloudrun" {
  service = "run.googleapis.com"

  # Prevents the API from being disabled when the resource is destroyed.
  disable_on_destroy = false
}

# Creates a Cloud Run service for this microservice.
resource "google_cloud_run_v2_service" "default" {
  name     = local.service_name
  location = local.region
  ingress  = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    execution_environment = "EXECUTION_ENVIRONMENT_GEN2"
    service_account = google_service_account.service.email

    containers {
      name = "app"
      # Note: This is not the actual image of the service as container lifecycle is managed outside of terraform
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      env {
        name = "ENABLE_CLOUD_LOGGING"
        value = "1"
      }

      env {
        name = "ENABLE_CLOUD_TRACE"
        value = "1"
      }

      env {
        name = "USE_CLOUD_TOKEN_PROVIDER"
        value = "1"
      }

      env {
        name = "USER_SVC_URL"
        value = "https://user-${data.google_project.default.number}.${local.region}.run.app"
      }

      env {
        name = "INCIDENTMODIFY_SVC_URL"
        value = "https://incidentmodify-${data.google_project.default.number}.${local.region}.run.app"
      }

      env {
        name = "CLIENT_SVC_URL"
        value = "https://client-${data.google_project.default.number}.${local.region}.run.app"
      }

      startup_probe {
        http_get {
          path = "/api/v1/health/${local.service_name}"
        }
      }

      liveness_probe {
        http_get {
          path = "/api/v1/health/${local.service_name}"
        }
      }

      # CPU is only allocated when processing requests
      resources {
        cpu_idle = true
        startup_cpu_boost = true
      }
    }
  }

  lifecycle {
    ignore_changes = [
      client,
      client_version,
      template[0].containers[0].image
    ] 
  }

  depends_on = [ google_project_service.cloudrun ]
}

# Configures access to this microservice.
data "google_iam_policy" "default" {
  binding {
    role = "roles/run.invoker"
    members = [
      data.google_service_account.apigateway.member
    ]
  }
}

resource "google_cloud_run_v2_service_iam_policy" "default" {
  project = google_cloud_run_v2_service.default.project
  location = google_cloud_run_v2_service.default.location
  name = google_cloud_run_v2_service.default.name
  policy_data = data.google_iam_policy.default.policy_data
}
