import React, { forwardRef } from 'react';
import { Select } from './Select.jsx';

export const BULAWAYO_SUBURBS = [
  'Bulawayo CBD',
  'Hillside',
  'Suburbs',
  'Famona',
  'North End',
  'Khumalo',
  'Burnside',
  'Riverside',
  'Pumula',
  'Cowdray Park',
  'Mahatshula',
  'Luveve',
  'Emakhandeni',
  'Nkulumane',
  'Entumbane',
];

export const SuburbSelect = forwardRef(function SuburbSelect(
  { label = 'Suburb', placeholder = 'Select a suburb', ...rest },
  ref
) {
  return (
    <Select ref={ref} label={label} {...rest}>
      <option value="">{placeholder}</option>
      {BULAWAYO_SUBURBS.map((s) => (
        <option key={s} value={s}>{s}</option>
      ))}
      <option value="Other">Other / not listed</option>
    </Select>
  );
});
