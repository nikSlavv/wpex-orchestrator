import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, Check } from 'lucide-react';

export default function CustomSelect({ options, value, onChange, placeholder = "Seleziona..." }) {
    const [isOpen, setIsOpen] = useState(false);
    const containerRef = useRef(null);

    const selectedOption = options.find(opt => opt.value === value);

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (containerRef.current && !containerRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleSelect = (optionValue) => {
        onChange(optionValue);
        setIsOpen(false);
    };

    return (
        <div
            className="custom-select-container"
            ref={containerRef}
            style={{ position: 'relative', width: '100%' }}
        >
            <div
                className={`custom-select-trigger ${isOpen ? 'open' : ''}`}
                onClick={() => setIsOpen(!isOpen)}
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '10px 14px',
                    background: 'var(--bg-secondary)',
                    border: `1px solid ${isOpen ? 'var(--accent-purple)' : 'var(--border-subtle)'}`,
                    borderRadius: 'var(--radius-sm)',
                    color: selectedOption ? 'var(--text-primary)' : 'var(--text-muted)',
                    cursor: 'pointer',
                    transition: 'var(--transition)',
                    boxShadow: isOpen ? '0 0 0 3px rgba(124, 106, 239, 0.15)' : 'none'
                }}
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {selectedOption?.icon && <span style={{ color: 'var(--accent-purple-light)' }}>{selectedOption.icon}</span>}
                    <span>{selectedOption ? selectedOption.label : placeholder}</span>
                </div>
                <ChevronDown
                    size={16}
                    style={{
                        transition: 'transform 0.3s ease',
                        transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                        color: 'var(--text-secondary)'
                    }}
                />
            </div>

            {isOpen && (
                <div
                    className="custom-select-dropdown"
                    style={{
                        position: 'absolute',
                        top: '100%',
                        left: 0,
                        right: 0,
                        marginTop: '6px',
                        background: 'var(--bg-card)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: 'var(--radius-sm)',
                        boxShadow: 'var(--shadow-hover)',
                        maxHeight: '240px',
                        overflowY: 'auto',
                        zIndex: 100,
                        backdropFilter: 'blur(10px)'
                    }}
                >
                    {options.map((opt) => (
                        <div
                            key={opt.value}
                            className={`custom-select-option ${value === opt.value ? 'selected' : ''}`}
                            onClick={() => handleSelect(opt.value)}
                            style={{
                                padding: '10px 14px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                cursor: 'pointer',
                                transition: 'background 0.2s ease',
                                background: value === opt.value ? 'rgba(124, 106, 239, 0.1)' : 'transparent',
                                color: value === opt.value ? 'var(--accent-purple-light)' : 'var(--text-primary)'
                            }}
                            onMouseEnter={e => { if (value !== opt.value) e.currentTarget.style.background = 'var(--bg-card-hover)'; }}
                            onMouseLeave={e => { if (value !== opt.value) e.currentTarget.style.background = 'transparent'; }}
                        >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                {opt.icon && <span>{opt.icon}</span>}
                                {opt.label}
                            </div>
                            {value === opt.value && <Check size={16} />}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
