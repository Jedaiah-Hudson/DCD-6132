import { useEffect, useState } from 'react';

export default function NaicsMultiSelect({ value, onChange }) {
  const [options, setOptions] = useState([]);

  useEffect(() => {
    const fetchNaics = async () => {
      try {
        const res = await fetch('http://127.0.0.1:8000/api/naics/');
        const data = await res.json();

        const formatted = data.map((item) => ({
          value: item.code,   // use code, not id
          label: `${item.code} - ${item.title}`,
        }));

        setOptions(formatted);
      } catch (err) {
        console.error('Failed to load NAICS codes', err);
      }
    };

    fetchNaics();
  }, []);

  return (
    <div style={{ minWidth: 300 }}>
      <label style={{ display: 'block', marginBottom: 6 }}>
        NAICS Codes
      </label>

      <select
        multiple
        value={value}
        onChange={(event) =>
          onChange(Array.from(event.target.selectedOptions, (option) => option.value))
        }
        style={{
          width: '100%',
          minHeight: 140,
          padding: 10,
          border: '1px solid #cfd4dc',
          borderRadius: 8,
          backgroundColor: '#ffffff',
        }}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
