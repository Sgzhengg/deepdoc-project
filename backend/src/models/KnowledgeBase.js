const mongoose = require('mongoose');

const knowledgeBaseSchema = new mongoose.Schema({
  name: {
    type: String,
    required: true,
    trim: true,
    maxlength: 100
  },
  description: {
    type: String,
    trim: true,
    maxlength: 500
  },
  owner: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true
  },
  documents: [{
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Document'
  }],
  isPublic: {
    type: Boolean,
    default: false
  },
  isShared: {
    type: Boolean,
    default: false
  },
  sharedWith: [{
    user: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User'
    },
    permission: {
      type: String,
      enum: ['read', 'write', 'admin'],
      default: 'read'
    }
  }],
  category: {
    type: String,
    trim: true
  },
  tags: [{
    type: String,
    trim: true
  }],
  settings: {
    autoUpdate: {
      type: Boolean,
      default: true
    },
    embeddingModel: {
      type: String,
      default: 'text-embedding-ada-002'
    },
    chunkSize: {
      type: Number,
      default: 1000
    },
    chunkOverlap: {
      type: Number,
      default: 200
    }
  },
  statistics: {
    documentCount: {
      type: Number,
      default: 0
    },
    totalSize: {
      type: Number,
      default: 0
    },
    lastUpdated: {
      type: Date,
      default: Date.now
    }
  }
}, {
  timestamps: true
});

knowledgeBaseSchema.index({ owner: 1, createdAt: -1 });
knowledgeBaseSchema.index({ name: 'text', description: 'text' });

module.exports = mongoose.model('KnowledgeBase', knowledgeBaseSchema);