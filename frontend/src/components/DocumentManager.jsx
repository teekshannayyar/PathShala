import React, { useState, useEffect } from 'react';
import { getDocuments, renameDocument, moveDocumentToFolder, bulkDeleteDocuments, deleteDocument } from '../api';
import { Folder, FileText, MoreVertical, Edit2, Trash2, FolderPlus, Loader2, CheckSquare, Square, FolderInput } from 'lucide-react';
import toast from 'react-hot-toast';
import { useNavigate } from 'react-router-dom';
import './DocumentManager.css';

export default function DocumentManager({ onDocumentSelect }) {
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState("");
  
  const [movingId, setMovingId] = useState(null);
  const [newFolderName, setNewFolderName] = useState("");
  const navigate = useNavigate();

  const loadDocs = async () => {
    try {
      setIsLoading(true);
      const docs = await getDocuments();
      setDocuments(docs);
    } catch (err) {
      toast.error("Failed to load documents");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDocs();
  }, []);

  const toggleSelect = (id) => {
    const newSet = new Set(selectedIds);
    if (newSet.has(id)) newSet.delete(id);
    else newSet.add(id);
    setSelectedIds(newSet);
  };

  const toggleSelectAll = (folderDocs) => {
    const newSet = new Set(selectedIds);
    const allSelected = folderDocs.every(d => newSet.has(d.id));
    if (allSelected) {
      folderDocs.forEach(d => newSet.delete(d.id));
    } else {
      folderDocs.forEach(d => newSet.add(d.id));
    }
    setSelectedIds(newSet);
  };

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return;
    if (!window.confirm(`Are you sure you want to delete ${selectedIds.size} documents?`)) return;

    const promise = bulkDeleteDocuments(Array.from(selectedIds));
    toast.promise(promise, {
      loading: 'Deleting documents...',
      success: 'Documents deleted successfully!',
      error: 'Failed to delete documents'
    });

    try {
      await promise;
      setDocuments(documents.filter(d => !selectedIds.has(d.id)));
      setSelectedIds(new Set());
    } catch (e) {}
  };

  const handleRename = async (id, currentName) => {
    if (!editName.trim() || editName === currentName) {
      setEditingId(null);
      return;
    }
    try {
      await renameDocument(id, editName);
      setDocuments(documents.map(d => d.id === id ? { ...d, filename: editName } : d));
      toast.success("Renamed successfully");
    } catch (err) {
      toast.error("Failed to rename");
    } finally {
      setEditingId(null);
    }
  };

  const handleMoveFolder = async (id, folder) => {
    if (!folder.trim()) return;
    try {
      await moveDocumentToFolder(id, folder);
      setDocuments(documents.map(d => d.id === id ? { ...d, folder } : d));
      toast.success(`Moved to ${folder}`);
    } catch (err) {
      toast.error("Failed to move document");
    } finally {
      setMovingId(null);
      setNewFolderName("");
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this document?")) return;
    try {
      await deleteDocument(id);
      setDocuments(documents.filter(d => d.id !== id));
      toast.success("Deleted successfully");
    } catch (err) {
      toast.error("Failed to delete");
    }
  };

  const openInChat = (doc) => {
    if (onDocumentSelect) onDocumentSelect(doc);
    navigate('/chat');
  };

  // Group by folder
  const groupedDocs = documents.reduce((acc, doc) => {
    const f = doc.folder || "Uncategorized";
    if (!acc[f]) acc[f] = [];
    acc[f].push(doc);
    return acc;
  }, {});

  const folders = Object.keys(groupedDocs).sort((a,b) => a === "Uncategorized" ? 1 : b === "Uncategorized" ? -1 : a.localeCompare(b));

  return (
    <div className="doc-manager-container animate-fade-in">
      <div className="doc-manager-header">
        <div>
          <h1>My Documents</h1>
          <p>Organize, rename, and manage your uploaded PDFs.</p>
        </div>
        {selectedIds.size > 0 && (
          <button className="btn-danger bulk-delete-btn animate-fade-in" onClick={handleBulkDelete}>
            <Trash2 size={16} /> Delete Selected ({selectedIds.size})
          </button>
        )}
      </div>

      {isLoading ? (
        <div className="centered"><Loader2 size={40} className="spin text-accent" /></div>
      ) : documents.length === 0 ? (
        <div className="empty-state glass">
          <FileText size={48} className="empty-icon" />
          <h4>No Documents Found</h4>
          <p>Upload a PDF to get started.</p>
          <button className="btn-primary mt-3" onClick={() => navigate('/chat')}>Go to Chat</button>
        </div>
      ) : (
        <div className="folder-list">
          {folders.map(folder => {
            const folderDocs = groupedDocs[folder];
            const allSelected = folderDocs.every(d => selectedIds.has(d.id));
            const someSelected = folderDocs.some(d => selectedIds.has(d.id));
            
            return (
              <div key={folder} className="folder-section">
                <div className="folder-header glass">
                  <div className="folder-title" onClick={() => toggleSelectAll(folderDocs)}>
                    {allSelected ? <CheckSquare size={18} className="text-accent" /> : <Square size={18} className={someSelected ? "text-accent" : ""} />}
                    <Folder className="text-accent" size={20} />
                    <h3>{folder}</h3>
                    <span className="badge">{folderDocs.length}</span>
                  </div>
                </div>

                <div className="folder-items">
                  {folderDocs.map(doc => (
                    <div key={doc.id} className={`doc-row glass ${selectedIds.has(doc.id) ? 'selected' : ''}`}>
                      <div className="doc-checkbox" onClick={() => toggleSelect(doc.id)}>
                        {selectedIds.has(doc.id) ? <CheckSquare size={18} className="text-accent" /> : <Square size={18} />}
                      </div>
                      
                      <div className="doc-info-main" onClick={() => openInChat(doc)}>
                        <FileText size={18} className="doc-icon" />
                        {editingId === doc.id ? (
                          <input 
                            autoFocus
                            type="text" 
                            className="inline-edit-input"
                            value={editName}
                            onChange={(e) => setEditName(e.target.value)}
                            onClick={(e) => e.stopPropagation()}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') handleRename(doc.id, doc.filename);
                              if (e.key === 'Escape') setEditingId(null);
                            }}
                            onBlur={() => handleRename(doc.id, doc.filename)}
                          />
                        ) : (
                          <span className="doc-name">{doc.filename}</span>
                        )}
                      </div>

                      <div className="doc-actions">
                        {movingId === doc.id ? (
                          <div className="move-dropdown" onClick={e => e.stopPropagation()}>
                            <input 
                              autoFocus
                              type="text" 
                              placeholder="New or existing folder..." 
                              value={newFolderName}
                              onChange={e => setNewFolderName(e.target.value)}
                              className="folder-input"
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') handleMoveFolder(doc.id, newFolderName);
                                if (e.key === 'Escape') setMovingId(null);
                              }}
                            />
                            <button className="btn-sm btn-primary" onClick={() => handleMoveFolder(doc.id, newFolderName)}>Move</button>
                            <button className="btn-sm" onClick={() => setMovingId(null)}>Cancel</button>
                          </div>
                        ) : (
                          <>
                            <button className="icon-btn" title="Rename" onClick={(e) => { e.stopPropagation(); setEditingId(doc.id); setEditName(doc.filename); }}>
                              <Edit2 size={16} />
                            </button>
                            <button className="icon-btn" title="Move to Folder" onClick={(e) => { e.stopPropagation(); setMovingId(doc.id); setNewFolderName(doc.folder || ""); }}>
                              <FolderInput size={16} />
                            </button>
                            <button className="icon-btn danger" title="Delete" onClick={(e) => { e.stopPropagation(); handleDelete(doc.id); }}>
                              <Trash2 size={16} />
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
