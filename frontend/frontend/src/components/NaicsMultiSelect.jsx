import Select from 'react-select';
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

  // convert ["541511"] into select objects
  const selectedOptions = options.filter((option) =>
    value.includes(option.value)
  );

  return (
    <div style={{ minWidth: 300 }}>
      <label style={{ display: 'block', marginBottom: 6 }}>
        NAICS Codes
      </label>

      <Select
        isMulti
        options={options}
        value={selectedOptions}
        onChange={(selected) =>
          onChange(selected.map((item) => item.value))
        }
        placeholder="Select NAICS codes..."
        classNamePrefix="naics-select"
      />
    </div>
  );
}