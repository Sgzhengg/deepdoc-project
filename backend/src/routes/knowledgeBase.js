const express = require('express');
const router = express.Router();

router.get('/', (req, res) => {
  res.json({ message: 'Knowledge Base endpoint - implementation pending' });
});

module.exports = router;