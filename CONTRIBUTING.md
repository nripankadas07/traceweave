# Contributing

TraceWeave is a local-first research prototype. Good contributions are small,
auditable, and backed by tests or a reproducible trace fixture.

Before opening a pull request:

- run `python -m unittest discover -s tests -v`;
- keep trace examples free of secrets, private prompts, and customer data;
- document new metrics with their limits and failure cases;
- avoid hosted-service requirements in the default path.

