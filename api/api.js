const { handler } = require('../netlify/functions/api');

exports.handler = async (event, context) => {
  return await handler(event, context);
};