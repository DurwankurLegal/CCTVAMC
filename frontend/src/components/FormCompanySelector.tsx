import React, { useEffect } from "react";
import { Form, Select } from "antd";
import { useDispatch, useSelector } from "react-redux";
import { RootState, AppDispatch } from "../store";
import { fetchCompanies } from "../store/companySlice";

interface FormCompanySelectorProps {
  isNew: boolean;
}

export const FormCompanySelector: React.FC<FormCompanySelectorProps> = ({ isNew }) => {
  const dispatch = useDispatch<AppDispatch>();
  const form = Form.useFormInstance();
  
  const { list: companies, defaultCompany, loading } = useSelector(
    (state: RootState) => state.companies
  );

  useEffect(() => {
    if (companies.length === 0) {
      dispatch(fetchCompanies());
    }
  }, [dispatch, companies.length]);

  useEffect(() => {
    if (isNew && defaultCompany && form) {
      // Auto-populate form company_id field with the default company ID
      form.setFieldValue("company_id", defaultCompany.id);
    }
  }, [isNew, defaultCompany, form]);

  return (
    <Form.Item
      name="company_id"
      label="Operating Company"
      rules={[{ required: true, message: "Please select the operating company" }]}
    >
      <Select
        loading={loading}
        disabled={!isNew}
        placeholder="Select operating company"
        options={companies.map((c) => ({
          label: `${c.name} ${c.is_default ? "(Default)" : ""}`,
          value: c.id,
        }))}
      />
    </Form.Item>
  );
};
