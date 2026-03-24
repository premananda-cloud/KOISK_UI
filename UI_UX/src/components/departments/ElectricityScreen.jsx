/**
 * ElectricityScreen.jsx
 * Services: Pay Bill | New Connection | Meter Change | Service Transfer
 * Pay Bill → PaymentFlow (backend /api/v1/payments/*)
 * Others   → ServiceRequestForm (backend /api/v1/electricity/*)
 */
import ServiceLayout      from './ServiceLayout';
import ServiceRequestForm from './ServiceRequestForm';

const TILES = [
  { action: 'pay_bill',   icon: '💳', label: 'Pay Bill',          sub: 'Pay your electricity bill' },
  { action: 'new_conn',   icon: '🔌', label: 'New Connection',    sub: 'Apply for new electricity' },
  { action: 'meter',      icon: '🔧', label: 'Meter Change',      sub: 'Request meter replacement' },
  { action: 'transfer',   icon: '📋', label: 'Service Transfer',  sub: 'Transfer to another person' },
];

function NewConnectionForm({ onClose }) {
  return (
    <ServiceRequestForm
      title="New Electricity Connection"
      icon="🔌"
      dept="electricity"
      endpoint="new-connection"
      onClose={onClose}
      fields={[
        { name: 'full_name',    label: 'Full Name',         type: 'text',     placeholder: 'e.g. Ramesh Kumar',      required: true  },
        { name: 'address',      label: 'Address',           type: 'textarea', placeholder: 'Full address with pin',   required: true  },
        { name: 'phone',        label: 'Mobile Number',     type: 'tel',      placeholder: '10-digit number',         required: true  },
        { name: 'id_proof',     label: 'ID Proof Type',     type: 'select',   required: true, options: [
            { value: 'aadhaar', label: 'Aadhaar Card' },
            { value: 'pan',     label: 'PAN Card'     },
            { value: 'voter',   label: 'Voter ID'     },
          ]},
        { name: 'id_number',    label: 'ID Number',         type: 'text',     placeholder: 'e.g. XXXX-XXXX-XXXX',    required: true  },
        { name: 'load_type',    label: 'Connection Type',   type: 'select',   required: true, options: [
            { value: 'domestic',    label: 'Domestic'      },
            { value: 'commercial',  label: 'Commercial'    },
            { value: 'industrial',  label: 'Industrial'    },
          ]},
      ]}
    />
  );
}

function MeterChangeForm({ onClose }) {
  return (
    <ServiceRequestForm
      title="Meter Change Request"
      icon="🔧"
      dept="electricity"
      endpoint="meter-change"
      onClose={onClose}
      fields={[
        { name: 'consumer_no',  label: 'Consumer Number',   type: 'text',     placeholder: 'e.g. KA-ELEC-204817',    required: true  },
        { name: 'full_name',    label: 'Full Name',         type: 'text',     placeholder: 'Name on account',         required: true  },
        { name: 'reason',       label: 'Reason',            type: 'select',   required: true, options: [
            { value: 'faulty',    label: 'Faulty Meter'     },
            { value: 'damaged',   label: 'Physically Damaged' },
            { value: 'upgrade',   label: 'Smart Meter Upgrade' },
          ]},
        { name: 'description',  label: 'Additional Details', type: 'textarea', placeholder: 'Describe the issue',     required: false },
      ]}
    />
  );
}

function ServiceTransferForm({ onClose }) {
  return (
    <ServiceRequestForm
      title="Service Transfer"
      icon="📋"
      dept="electricity"
      endpoint="transfer-service"
      onClose={onClose}
      fields={[
        { name: 'consumer_no',     label: 'Consumer Number',       type: 'text',     placeholder: 'e.g. KA-ELEC-204817', required: true  },
        { name: 'current_name',    label: 'Current Account Holder', type: 'text',    placeholder: 'Full name',            required: true  },
        { name: 'new_name',        label: 'New Account Holder',    type: 'text',     placeholder: 'Full name',            required: true  },
        { name: 'new_phone',       label: 'New Holder Mobile',     type: 'tel',      placeholder: '10-digit number',      required: true  },
        { name: 'transfer_reason', label: 'Transfer Reason',       type: 'select',   required: true, options: [
            { value: 'sale',       label: 'Property Sale'      },
            { value: 'inheritance',label: 'Inheritance'        },
            { value: 'other',      label: 'Other'              },
          ]},
      ]}
    />
  );
}

const FORM_MODALS = {
  new_conn: NewConnectionForm,
  meter:    MeterChangeForm,
  transfer: ServiceTransferForm,
};

export default function ElectricityScreen() {
  return (
    <ServiceLayout
      dept="electricity"
      icon="⚡"
      gradient="bg-gradient-to-r from-amber-500 to-orange-500"
      title="Electricity Services"
      tiles={TILES}
      formModals={FORM_MODALS}
    />
  );
}
