// Copia este archivo a config.js y ajusta los valores tras terraform apply
// Usa los outputs "website_bucket" y "website_url" de Terraform

window.APP_CONFIG = {
  websiteBucket: "REPLACE_WITH_OUTPUT_website_bucket", // p.ej. mi-website-bucket-demo
  resultsPrefix: "results",
  websiteEndpoint: "REPLACE_WITH_OUTPUT_website_url"   // p.ej. mi-website-bucket-demo.s3-website-us-east-1.amazonaws.com
};
