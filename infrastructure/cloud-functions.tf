// Configure the Yandex.Cloud provider
provider "yandex" {
  token                    = "auth_token_here"
  service_account_key_file = "path_to_service_account_key_file"
  cloud_id                 = "cloud_id_here"
  folder_id                = "folder_id_here"
  zone                     = "ru-central1-a"
}

// Create Cloud Functions Version
resource "yandex_function" "test-function" {
  name               = "some_name"
  description        = "any description"
  user_hash          = "any_user_defined_string"
  runtime            = "python37"
  entrypoint         = "main"
  memory             = "128"
  execution_timeout  = "10"
  service_account_id = "are1service2account3id"
  tags               = ["my_tag"]
  content {
    zip_filename = "function.zip"
  }
}
