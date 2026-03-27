const mongoose = require('mongoose');

const documentSchema = new mongoose.Schema({
  title: {
    type: String,
    required: true,
    trim: true,
    maxlength: 200
  },
  description: {
    type: String,
    trim: true,
    maxlength: 1000
  },
  fileName: {
    type: String,
    required: true,
    trim: true
  },
  originalName: {
    type: String,
    required: true,
    trim: true
  },
  mimeType: {
    type: String,
    required: true
  },
  size: {
    type: Number,
    required: true
  },
  filePath: {
    type: String,
    required: true
  },
  content: {
    type: String,
    default: ''
  },
  extractedText: {
    type: String,
    default: ''
  },
  fileType: {
    type: String,
    enum: ['pdf', 'doc', 'docx', 'txt', 'rtf', 'xls', 'xlsx', 'ppt', 'pptx', 'jpg', 'jpeg', 'png', 'gif', 'mp3', 'wav', 'mp4', 'avi', 'mov'],
    required: true
  },
  owner: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true
  },
  tags: [{
    type: String,
    trim: true
  }],
  category: {
    type: String,
    trim: true
  },
  department: {
    type: String,
    trim: true
  },
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
  version: {
    type: Number,
    default: 1
  },
  parentDocument: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Document'
  },
  status: {
    type: String,
    enum: ['processing', 'completed', 'failed', 'pending'],
    default: 'pending'
  },
  aiAnalysis: {
    summary: {
      type: String,
      default: ''
    },
    keywords: [{
      type: String
    }],
    entities: [{
      text: String,
      label: String,
      confidence: Number
    }],
    sentiment: {
      score: Number,
      label: String
    },
    topics: [{
      topic: String,
      confidence: Number
    }],
    language: {
      type: String,
      default: 'en'
    }
  },
  metadata: {
    pageCount: Number,
    wordCount: Number,
    createdAt: Date,
    modifiedAt: Date,
    author: String,
    subject: String,
    creator: String,
    producer: String
  },
  searchVector: {
    type: [Number],
    index: '2dsphere'
  },
  thumbnails: [{
    page: Number,
    path: String,
    width: Number,
    height: Number
  }],
  processingLog: [{
    timestamp: {
      type: Date,
      default: Date.now
    },
    step: String,
    status: String,
    message: String,
    duration: Number
  }],
  lastAccessed: {
    type: Date,
    default: Date.now
  },
  accessCount: {
    type: Number,
    default: 0
  }
}, {
  timestamps: true
});

documentSchema.index({ title: 'text', content: 'text', extractedText: 'text', tags: 'text', description: 'text' });
documentSchema.index({ owner: 1, createdAt: -1 });
documentSchema.index({ fileType: 1 });
documentSchema.index({ category: 1 });
documentSchema.index({ department: 1 });
documentSchema.index({ 'aiAnalysis.keywords': 1 });
documentSchema.index({ tags: 1 });

module.exports = mongoose.model('Document', documentSchema);