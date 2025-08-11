// Copia este archivo a config.js y ajusta los valores tras terraform apply
// Usa los outputs "website_bucket" y "website_url" de Terraform

window.APP_CONFIG = {
  websiteBucket: "tu-website-bucket-unico-1234", // p.ej. mi-website-bucket-demo
  resultsPrefix: "results",
  websiteEndpoint: "tu-website-bucket-unico-1234.s3-website-us-east-1.amazonaws.com"   // p.ej. mi-website-bucket-demo.s3-website-us-east-1.amazonaws.com
};




