
require("dotenv").config();
const { LanceDb } = require("./utils/vectorDbProviders/lance");
console.log("LanceDB URI:", LanceDb.uri);
