import { useState } from "react";
import { Card, Form, Input, Button, Typography, message } from "antd";
import { LockOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useDispatch } from "react-redux";
import apiClient, { apiErrorMessage } from "../api/client";
import { fetchMe } from "../store/authSlice";
import type { AppDispatch } from "../store";

const { Title, Paragraph } = Typography;

/**
 * Shown when /auth/me reports must_change_password (e.g. a provisioned admin
 * still using its one-time temp password). The user cannot reach the app until
 * the password is changed.
 */
export default function ForceChangePassword() {
  const dispatch = useDispatch<AppDispatch>();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  const onFinish = async (values: {
    current_password: string;
    new_password: string;
    confirm: string;
  }) => {
    setSaving(true);
    try {
      await apiClient.post("/auth/change-password", {
        current_password: values.current_password,
        new_password: values.new_password,
      });
      message.success("Password updated");
      // Refresh identity so the must_change_password flag clears, then proceed.
      await dispatch(fetchMe());
      navigate("/dashboard", { replace: true });
    } catch (err) {
      message.error(apiErrorMessage(err, "Could not change password"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center",
      justifyContent: "center", background: "#0b0f19" }}>
      <Card style={{ width: 400 }}>
        <Title level={3} style={{ marginBottom: 4 }}>Set a new password</Title>
        <Paragraph type="secondary">
          For security, you must replace the temporary password before continuing.
        </Paragraph>
        <Form form={form} layout="vertical" onFinish={onFinish}>
          <Form.Item name="current_password" label="Current (temporary) password"
            rules={[{ required: true, message: "Enter your current password" }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="Temporary password" />
          </Form.Item>
          <Form.Item name="new_password" label="New password"
            rules={[
              { required: true, message: "Enter a new password" },
              { min: 8, message: "At least 8 characters" },
            ]}>
            <Input.Password prefix={<LockOutlined />} placeholder="New password" />
          </Form.Item>
          <Form.Item name="confirm" label="Confirm new password" dependencies={["new_password"]}
            rules={[
              { required: true, message: "Confirm your new password" },
              ({ getFieldValue }) => ({
                validator: (_, value) =>
                  !value || getFieldValue("new_password") === value
                    ? Promise.resolve()
                    : Promise.reject(new Error("Passwords do not match")),
              }),
            ]}>
            <Input.Password prefix={<LockOutlined />} placeholder="Confirm new password" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={saving}>
            Update password
          </Button>
        </Form>
      </Card>
    </div>
  );
}
