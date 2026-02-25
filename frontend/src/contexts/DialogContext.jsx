import React, { createContext, useContext, useState, useCallback } from 'react';

const DialogContext = createContext();

export function DialogProvider({ children }) {
    const [dialogs, setDialogs] = useState([]);

    const openDialog = useCallback((options) => {
        return new Promise((resolve) => {
            const id = Date.now().toString() + Math.random().toString(36).substring(2);
            const dialog = {
                id,
                ...options,
                onClose: (result) => {
                    setDialogs((prev) => prev.filter((d) => d.id !== id));
                    resolve(result);
                }
            };
            setDialogs((prev) => [...prev, dialog]);
        });
    }, []);

    const confirm = useCallback((message, options = {}) => {
        return openDialog({
            type: 'confirm',
            message,
            title: options.title || 'Conferma Operazione',
            confirmText: options.confirmText || 'Conferma',
            cancelText: options.cancelText || 'Annulla',
            danger: options.danger || false,
        });
    }, [openDialog]);

    const alert = useCallback((message, options = {}) => {
        return openDialog({
            type: 'alert',
            message,
            title: options.title || 'Attenzione',
            confirmText: options.confirmText || 'OK',
        });
    }, [openDialog]);

    const prompt = useCallback((message, options = {}) => {
        return openDialog({
            type: 'prompt',
            message,
            title: options.title || 'Inserisci Valore',
            confirmText: options.confirmText || 'Conferma',
            cancelText: options.cancelText || 'Annulla',
            defaultValue: options.defaultValue || '',
        });
    }, [openDialog]);

    return (
        <DialogContext.Provider value={{ confirm, alert, prompt }}>
            {children}
            {dialogs.length > 0 && (
                <div className="custom-dialog-backdrop">
                    {dialogs.map((dialog, index) => (
                        <div key={dialog.id} className="custom-dialog-wrapper" style={{ zIndex: 10000 + index }}>
                            <div className="custom-dialog">
                                <div className="custom-dialog-header">
                                    <h3>{dialog.title}</h3>
                                </div>
                                <div className="custom-dialog-body">
                                    <p>{dialog.message}</p>
                                    {dialog.type === 'prompt' && (
                                        <input
                                            type="text"
                                            className="input"
                                            placeholder={dialog.placeholder || ''}
                                            defaultValue={dialog.defaultValue || ''}
                                            autoFocus
                                            style={{ marginTop: 12, width: '100%' }}
                                            onChange={(e) => dialog.inputValue = e.target.value}
                                            onKeyDown={(e) => {
                                                if (e.key === 'Enter') dialog.onClose(dialog.inputValue || dialog.defaultValue);
                                            }}
                                        />
                                    )}
                                </div>
                                <div className="custom-dialog-footer">
                                    {(dialog.type === 'confirm' || dialog.type === 'prompt') && (
                                        <button className="btn" onClick={() => dialog.onClose(null)}>
                                            {dialog.cancelText}
                                        </button>
                                    )}
                                    <button
                                        className={`btn ${dialog.danger ? 'btn-danger' : 'btn-primary'}`}
                                        onClick={() => dialog.onClose(dialog.type === 'prompt' ? (dialog.inputValue !== undefined ? dialog.inputValue : dialog.defaultValue) : true)}
                                    >
                                        {dialog.confirmText}
                                    </button>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </DialogContext.Provider>
    );
}

export function useDialog() {
    return useContext(DialogContext);
}
