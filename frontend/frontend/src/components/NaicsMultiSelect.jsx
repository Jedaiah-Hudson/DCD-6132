import { useEffect, useState } from 'react';
import Select from 'react-select';

export default function NaicsMultiSelect({ value, onChange }) {
  const [options, setOptions] = useState([]);

  useEffect(() => {
    const fetchNaics = async () => {
      try {
        const res = await fetch('http://127.0.0.1:8000/api/naics/');
        const data = await res.json();

        const formatted = data.map((item) => ({
          value: item.code,
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

      <Select
        isMulti
        isSearchable
        options={options}
        value={options.filter((opt) => value?.includes(opt.value))}
        onChange={(selected) =>
          onChange(selected ? selected.map((s) => s.value) : [])
        }
      />
    </div>
  );
}