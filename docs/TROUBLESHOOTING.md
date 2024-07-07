# Troubleshooting

## I didn't get an email
CourseWatch notifies by creating a GitHub Issue. GitHub emails you when:
- You are watching the repository, or
- You receive notifications for issues in your notification settings.

Try:
- Open the repo **Issues** tab and confirm an Issue was created.
- In GitHub, click **Watch** → choose **All Activity**.
- Check GitHub notification settings for email delivery.

## The tool says it can't extract the number
- Confirm the page is public and contains text like `Availability no: 1`.
- Sometimes the wording differs. Update `watchlist.yml` keyword.
- If the page has multiple "Availability" values, we may need a more specific parser.

## GitHub Actions isn't running
- Ensure Actions are enabled (Actions tab).
- Ensure the workflow file exists at `.github/workflows/check.yml`.
