const { handler } = require('@netlify/functions');
const { app } = require('../netlify/functions/api');
const { Mangum } = require('mangum');

exports.handler = async (event, context) => {
  const mangum = new Mangum(app);
  return await mangum(event, context);
};