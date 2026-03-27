const express = require('express');
const router = express.Router();
const multer = require('multer');
const Document = require('../models/Document');
const DocumentProcessor = require('../services/documentProcessor');
const upload = require('../middleware/upload');
const { auth } = require('../middleware/auth');

const documentProcessor = new DocumentProcessor();

router.post('/upload', auth, upload.array('files', 10), async (req, res) => {
  try {
    if (!req.files || req.files.length === 0) {
      return res.status(400).json({ error: 'No files uploaded' });
    }

    const uploadedDocuments = [];

    for (const file of req.files) {
      const { title, description, tags, category, department } = req.body;
      
      const processingResult = await documentProcessor.processDocument(
        file.path,
        file.mimetype,
        {
          originalName: file.originalname,
          size: file.size,
          ...JSON.parse(req.body.metadata || '{}')
        }
      );

      const document = new Document({
        title: title || file.originalname,
        description: description || '',
        fileName: file.filename,
        originalName: file.originalname,
        mimeType: file.mimetype,
        size: file.size,
        filePath: file.path,
        content: processingResult.text,
        extractedText: processingResult.text,
        fileType: getFileType(file.mimetype),
        owner: req.user._id,
        tags: tags ? tags.split(',').map(tag => tag.trim()) : [],
        category: category || '',
        department: department || req.user.department || '',
        metadata: {
          ...processingResult.metadata,
          pageCount: processingResult.pageCount,
          wordCount: processingResult.wordCount,
          processingTime: processingResult.processingTime
        },
        thumbnails: processingResult.thumbnails,
        status: processingResult.success ? 'completed' : 'failed'
      });

      await document.save();
      uploadedDocuments.push(document);
    }

    res.status(201).json({
      message: 'Files uploaded and processed successfully',
      documents: uploadedDocuments
    });
  } catch (error) {
    console.error('Upload error:', error);
    res.status(500).json({ error: 'Failed to upload files', details: error.message });
  }
});

router.get('/', auth, async (req, res) => {
  try {
    const {
      page = 1,
      limit = 20,
      search,
      fileType,
      category,
      department,
      tags,
      sortBy = 'createdAt',
      sortOrder = 'desc'
    } = req.query;

    const query = { owner: req.user._id };

    if (search) {
      query.$text = { $search: search };
    }

    if (fileType) {
      query.fileType = fileType;
    }

    if (category) {
      query.category = category;
    }

    if (department) {
      query.department = department;
    }

    if (tags) {
      query.tags = { $in: tags.split(',') };
    }

    const sort = {};
    sort[sortBy] = sortOrder === 'desc' ? -1 : 1;

    const documents = await Document.find(query)
      .populate('owner', 'username firstName lastName email')
      .sort(sort)
      .limit(limit * 1)
      .skip((page - 1) * limit)
      .exec();

    const total = await Document.countDocuments(query);

    res.json({
      documents,
      totalPages: Math.ceil(total / limit),
      currentPage: page,
      total
    });
  } catch (error) {
    console.error('Get documents error:', error);
    res.status(500).json({ error: 'Failed to retrieve documents' });
  }
});

router.get('/:id', auth, async (req, res) => {
  try {
    const document = await Document.findById(req.params.id)
      .populate('owner', 'username firstName lastName email')
      .populate('sharedWith.user', 'username firstName lastName email');

    if (!document) {
      return res.status(404).json({ error: 'Document not found' });
    }

    if (document.owner._id.toString() !== req.user._id.toString() && 
        !document.isPublic && 
        !document.sharedWith.some(share => share.user._id.toString() === req.user._id.toString())) {
      return res.status(403).json({ error: 'Access denied' });
    }

    document.accessCount += 1;
    document.lastAccessed = new Date();
    await document.save();

    res.json(document);
  } catch (error) {
    console.error('Get document error:', error);
    res.status(500).json({ error: 'Failed to retrieve document' });
  }
});

router.put('/:id', auth, async (req, res) => {
  try {
    const { title, description, tags, category, department, isPublic } = req.body;
    
    const document = await Document.findById(req.params.id);
    
    if (!document) {
      return res.status(404).json({ error: 'Document not found' });
    }

    if (document.owner.toString() !== req.user._id.toString()) {
      return res.status(403).json({ error: 'Access denied' });
    }

    document.title = title || document.title;
    document.description = description || document.description;
    document.tags = tags ? tags.split(',').map(tag => tag.trim()) : document.tags;
    document.category = category || document.category;
    document.department = department || document.department;
    document.isPublic = isPublic !== undefined ? isPublic : document.isPublic;

    await document.save();
    res.json(document);
  } catch (error) {
    console.error('Update document error:', error);
    res.status(500).json({ error: 'Failed to update document' });
  }
});

router.delete('/:id', auth, async (req, res) => {
  try {
    const document = await Document.findById(req.params.id);
    
    if (!document) {
      return res.status(404).json({ error: 'Document not found' });
    }

    if (document.owner.toString() !== req.user._id.toString()) {
      return res.status(403).json({ error: 'Access denied' });
    }

    await Document.findByIdAndDelete(req.params.id);
    res.json({ message: 'Document deleted successfully' });
  } catch (error) {
    console.error('Delete document error:', error);
    res.status(500).json({ error: 'Failed to delete document' });
  }
});

router.post('/:id/share', auth, async (req, res) => {
  try {
    const { users, permission = 'read' } = req.body;
    
    const document = await Document.findById(req.params.id);
    
    if (!document) {
      return res.status(404).json({ error: 'Document not found' });
    }

    if (document.owner.toString() !== req.user._id.toString()) {
      return res.status(403).json({ error: 'Access denied' });
    }

    document.sharedWith = users.map(userId => ({
      user: userId,
      permission
    }));
    document.isShared = true;

    await document.save();
    res.json(document);
  } catch (error) {
    console.error('Share document error:', error);
    res.status(500).json({ error: 'Failed to share document' });
  }
});

router.get('/search/advanced', auth, async (req, res) => {
  try {
    const {
      query,
      fileType,
      category,
      department,
      tags,
      dateFrom,
      dateTo,
      sizeMin,
      sizeMax,
      page = 1,
      limit = 20
    } = req.query;

    const searchQuery = {
      $and: [
        { owner: req.user._id },
        { status: 'completed' }
      ]
    };

    if (query) {
      searchQuery.$and.push({
        $or: [
          { title: { $regex: query, $options: 'i' } },
          { description: { $regex: query, $options: 'i' } },
          { content: { $regex: query, $options: 'i' } },
          { tags: { $in: [new RegExp(query, 'i')] } }
        ]
      });
    }

    if (fileType) {
      searchQuery.$and.push({ fileType });
    }

    if (category) {
      searchQuery.$and.push({ category });
    }

    if (department) {
      searchQuery.$and.push({ department });
    }

    if (tags) {
      searchQuery.$and.push({ tags: { $in: tags.split(',') } });
    }

    if (dateFrom || dateTo) {
      const dateFilter = {};
      if (dateFrom) dateFilter.$gte = new Date(dateFrom);
      if (dateTo) dateFilter.$lte = new Date(dateTo);
      searchQuery.$and.push({ createdAt: dateFilter });
    }

    if (sizeMin || sizeMax) {
      const sizeFilter = {};
      if (sizeMin) sizeFilter.$gte = parseInt(sizeMin);
      if (sizeMax) sizeFilter.$lte = parseInt(sizeMax);
      searchQuery.$and.push({ size: sizeFilter });
    }

    const documents = await Document.find(searchQuery)
      .populate('owner', 'username firstName lastName email')
      .sort({ createdAt: -1 })
      .limit(limit * 1)
      .skip((page - 1) * limit)
      .exec();

    const total = await Document.countDocuments(searchQuery);

    res.json({
      documents,
      totalPages: Math.ceil(total / limit),
      currentPage: page,
      total
    });
  } catch (error) {
    console.error('Advanced search error:', error);
    res.status(500).json({ error: 'Failed to search documents' });
  }
});

function getFileType(mimeType) {
  const typeMap = {
    'application/pdf': 'pdf',
    'application/msword': 'doc',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
    'text/plain': 'txt',
    'text/rtf': 'rtf',
    'application/vnd.ms-excel': 'xls',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
    'application/vnd.ms-powerpoint': 'ppt',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
    'image/jpeg': 'jpg',
    'image/png': 'png',
    'image/gif': 'gif',
    'audio/mpeg': 'mp3',
    'audio/wav': 'wav',
    'video/mp4': 'mp4',
    'video/avi': 'avi',
    'video/quicktime': 'mov'
  };
  return typeMap[mimeType] || 'unknown';
}

module.exports = router;