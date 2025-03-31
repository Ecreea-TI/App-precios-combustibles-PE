const { createRequestHandler } = require('@netlify/functions');
const { app } = require('../main');

module.exports.handler = createRequestHandler({
  app,
  callback: (req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  },
});