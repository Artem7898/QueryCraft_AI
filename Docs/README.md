# QueryCraft AI project guide

**English** · [Русский](README_RU.md)

## What it does

QueryCraft AI turns a description in English or Russian into a draft database query. You describe the result you want, select a database and a complexity level, and get query text with a short explanation. The browser displays the draft and lets you copy it. A person reviews it against the real schema before running it in their own database tools.

The project helps you move from a question such as “What was our revenue each week?” to a query you can inspect and refine. It is useful for analysts drafting a report, developers exploring a query pattern, and learners comparing how the same task is expressed in different dialects. The explanation helps you connect the request to the filter, join, or aggregation in the draft.

## What you can generate

| Target | Typical starting point |
| --- | --- |
| PostgreSQL | Filters, joins, aggregates, and more involved queries such as grouped reports |
| MySQL | Queries for applications and reports using MySQL syntax |
| SQLite | Queries for local databases, prototypes, and small datasets |
| MongoDB | Shell-style filter or aggregation expressions for document collections |

The form offers **Simple**, **Medium**, and **Advanced** complexity. In live mode, this choice guides the model toward a simpler or more involved query. The dialect setting tells the model which syntax to target. The form has Russian and English controls, the page offers example prompts, and the result uses syntax highlighting. The browser remembers the selected language and color theme.

## Choose a generation mode

| Mode | How it works | Use it for |
| --- | --- | --- |
| Demo | The API selects from built-in examples, including users, orders, and a generic query. It uses no external model call. | Trying the interface, checking the API locally, and developing without a Bytez key. |
| Live | The API sends the description and generation instructions to Bytez and returns the model’s draft. | Working with your own descriptions and requesting more specific queries. |

The demo returns templates for the selected dialect. For example, a prompt about users returns a built-in users query even if you ask for a different age threshold or ordering. A model identifier ending in `(тестовый режим)` marks a demo result.

[Start the local demo](../README.md#run-locally) · [Configure live generation](../README.md#configuration)

## From a question to a draft

1. Open the query form and describe the result you need. Include relevant table or collection names, columns or fields, known relationships, filters, grouping, and ordering.
2. Select the database dialect and complexity, then generate the draft. The result shows the query, its explanation, generation time, and model.
3. Compare the draft with your schema and the expected result. Check names, joins, date boundaries, null handling, and SQL or MongoDB syntax as applicable.
4. Copy the reviewed text into your usual query tool. Try it against representative test data before relying on it in a report or application.

### Example descriptions

| Goal | Description to enter | Target |
| --- | --- | --- |
| Review active users | “Using `users(id, email, age, status, created_at)`, list active users older than 25, newest first. Return at most 100 rows.” | PostgreSQL, Simple |
| Summarize daily sales | “Using `orders(created_at, amount, status)`, total completed orders and revenue by calendar day for the last 30 days. Sort newest day first.” | MySQL, Medium |
| Inspect a customer cohort | “In the `customers` collection, count active customers by country. Return countries with at least ten active customers and sort by count descending.” | MongoDB, Medium |

The examples show how to supply schema context and describe output precisely. Live generation uses those details. Demo results follow the built-in templates.

## What to expect from a result

QueryCraft AI generates text. It has no database connection, schema discovery, query execution, or access to query results. It does not verify that a query fits a particular dataset, database version, permissions model, or performance budget. The draft may contain a wrong identifier, unsupported syntax, or a different interpretation of the request.

In live mode, the description is sent to Bytez. Use schema names and synthetic values where possible, and keep credentials or sensitive records out of prompts. The Bytez key belongs in backend configuration.

## Technical documentation

The technical guide covers request flow, API behavior and errors, configuration, data boundaries, and how to verify or troubleshoot the application. [Technical guide](technical.md)
