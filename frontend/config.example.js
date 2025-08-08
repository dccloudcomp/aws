// Copia este archivo a config.js y ajusta los valores tras terraform apply
window.APP_CONFIG = {
  websiteBucket: "REPLACE_WITH_OUTPUT_website_bucket",
  resultsPrefix: "results",
  websiteEndpoint: "REPLACE_WITH_OUTPUT_website_url" // p.ej. my-bucket.s3-website-eu-west-1.amazonaws.com
};
