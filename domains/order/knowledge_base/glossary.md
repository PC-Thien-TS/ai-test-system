# Order Glossary

- `order status`: The backend-owned lifecycle state for an order.
- `payment attempt`: One attempt to collect payment for an order.
- `refund`: The money return flow triggered by valid cancel, reject, or late-webhook cases.
- `late webhook`: A payment success webhook that arrives after the order already reached a terminal state.
- `terminal state`: A final state that should not transition back into the normal fulfillment flow.
- `idempotency key`: A client-supplied key used to make retries safe for create and payment actions.
