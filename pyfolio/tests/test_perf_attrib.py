import numpy as np
import pandas as pd
import unittest
import warnings

import empyrical as ep
from pyfolio.perf_attrib import perf_attrib, create_perf_attrib_stats


def generate_toy_risk_model_output(start_date='2017-01-01', periods=10):
    """
    Generate toy risk model output.

    Parameters
    ----------
    start_date : str
        date to start generating toy data
    periods : int
        number of days for which to generate toy data

    Returns
    -------
    tuple of (returns, factor_returns, positions, factor_loadings)
    returns : pd.DataFrame
    factor_returns : pd.DataFrame
    """
    dts = pd.date_range(start_date, periods=periods)
    np.random.seed(123)
    tickers = ['AAPL', 'TLT', 'XOM']
    styles = ['factor1', 'factor2']

    returns = pd.Series(index=dts,
                        data=np.random.randn(periods)) / 100

    factor_returns = pd.DataFrame(
        columns=styles, index=dts,
        data=np.random.randn(periods, len(styles))) / 100

    arrays = [dts, tickers]
    index = pd.MultiIndex.from_product(arrays, names=['dt', 'ticker'])

    positions = pd.DataFrame(
        columns=tickers, index=dts,
        data=np.random.randint(100, size=(periods, len(tickers)))
    )
    positions['cash'] = np.zeros(periods)

    factor_loadings = pd.DataFrame(
        columns=styles, index=index,
        data=np.random.randn(periods * len(tickers), len(styles))
    )

    return returns, positions, factor_returns, factor_loadings


class PerfAttribTestCase(unittest.TestCase):

    def test_perf_attrib_simple(self):

        start_date = '2017-01-01'
        periods = 2
        dts = pd.date_range(start_date, periods=periods)
        dts.name = 'dt'

        tickers = ['stock1', 'stock2']
        styles = ['risk_factor1', 'risk_factor2']

        returns = pd.Series(data=[0.1, 0.1], index=dts)

        factor_returns = pd.DataFrame(
            columns=styles,
            index=dts,
            data={'risk_factor1': [.1, .1],
                  'risk_factor2': [.1, .1]}
        )

        positions = pd.DataFrame(
            index=dts,
            data={'stock1': [20, 20],
                  'stock2': [50, 50],
                  'cash': [0, 0]}
        )

        index = pd.MultiIndex.from_product(
            [dts, tickers], names=['dt', 'ticker'])

        factor_loadings = pd.DataFrame(
            columns=styles,
            index=index,
            data={'risk_factor1': [0.25, 0.25, 0.25, 0.25],
                  'risk_factor2': [0.25, 0.25, 0.25, 0.25]}
        )

        expected_perf_attrib_output = pd.DataFrame(
            index=dts,
            columns=['risk_factor1', 'risk_factor2', 'common_returns',
                     'specific_returns', 'total_returns'],
            data={'risk_factor1': [0.025, 0.025],
                  'risk_factor2': [0.025, 0.025],
                  'common_returns': [0.05, 0.05],
                  'specific_returns': [0.05, 0.05],
                  'total_returns': returns}
        )

        expected_exposures_portfolio = pd.DataFrame(
            index=dts,
            columns=['risk_factor1', 'risk_factor2'],
            data={'risk_factor1': [0.25, 0.25],
                  'risk_factor2': [0.25, 0.25]}
        )

        exposures_portfolio, perf_attrib_output = perf_attrib(returns,
                                                              positions,
                                                              factor_returns,
                                                              factor_loadings)

        pd.util.testing.assert_frame_equal(expected_perf_attrib_output,
                                           perf_attrib_output)

        pd.util.testing.assert_frame_equal(expected_exposures_portfolio,
                                           exposures_portfolio)

        # test long and short positions
        positions = pd.DataFrame(index=dts,
                                 data={'stock1': [20, 20],
                                       'stock2': [-20, -20],
                                       'cash': [20, 20]})

        exposures_portfolio, perf_attrib_output = perf_attrib(returns,
                                                              positions,
                                                              factor_returns,
                                                              factor_loadings)

        expected_perf_attrib_output = pd.DataFrame(
            index=dts,
            columns=['risk_factor1', 'risk_factor2', 'common_returns',
                     'specific_returns', 'total_returns'],
            data={'risk_factor1': [0.0, 0.0],
                  'risk_factor2': [0.0, 0.0],
                  'common_returns': [0.0, 0.0],
                  'specific_returns': [0.1, 0.1],
                  'total_returns': returns}
        )

        expected_exposures_portfolio = pd.DataFrame(
            index=dts,
            columns=['risk_factor1', 'risk_factor2'],
            data={'risk_factor1': [0.0, 0.0],
                  'risk_factor2': [0.0, 0.0]}
        )

        pd.util.testing.assert_frame_equal(expected_perf_attrib_output,
                                           perf_attrib_output)

        pd.util.testing.assert_frame_equal(expected_exposures_portfolio,
                                           exposures_portfolio)

    def test_perf_attrib_regression(self):

        positions = pd.read_csv('pyfolio/tests/test_data/positions.csv',
                                index_col=0, parse_dates=True)

        positions.columns = [int(col) if col != 'cash' else col
                             for col in positions.columns]

        returns = pd.read_csv('pyfolio/tests/test_data/returns.csv',
                              index_col=0, parse_dates=True,
                              header=None, squeeze=True)

        factor_loadings = pd.read_csv(
            'pyfolio/tests/test_data/factor_loadings.csv',
            index_col=[0, 1], parse_dates=True
        )

        factor_returns = pd.read_csv(
            'pyfolio/tests/test_data/factor_returns.csv',
            index_col=0, parse_dates=True
        )

        residuals = pd.read_csv('pyfolio/tests/test_data/residuals.csv',
                                index_col=0, parse_dates=True)

        residuals.columns = [int(col) for col in residuals.columns]

        intercepts = pd.read_csv('pyfolio/tests/test_data/intercepts.csv',
                                 index_col=0, header=None, squeeze=True)

        risk_exposures_portfolio, perf_attrib_output = perf_attrib(
            returns,
            positions,
            factor_returns,
            factor_loadings,
        )

        specific_returns = perf_attrib_output['specific_returns']
        common_returns = perf_attrib_output['common_returns']
        combined_returns = specific_returns + common_returns

        # since all returns are factor returns, common returns should be
        # equivalent to total returns, and specific returns should be 0
        pd.util.testing.assert_series_equal(returns,
                                            common_returns,
                                            check_names=False)

        self.assertTrue(np.isclose(specific_returns, 0).all())

        # specific and common returns combined should equal total returns
        pd.util.testing.assert_series_equal(returns,
                                            combined_returns,
                                            check_names=False)

        # check that residuals + intercepts = specific returns
        self.assertTrue(np.isclose((residuals + intercepts), 0).all())

        # check that exposure * factor returns = common returns
        expected_common_returns = risk_exposures_portfolio.multiply(
            factor_returns, axis='rows'
        ).sum(axis='columns')

        pd.util.testing.assert_series_equal(expected_common_returns,
                                            common_returns,
                                            check_names=False)

        # since factor loadings are ones, portfolio risk exposures
        # should be ones
        pd.util.testing.assert_frame_equal(
            risk_exposures_portfolio,
            pd.DataFrame(np.ones_like(risk_exposures_portfolio),
                         index=risk_exposures_portfolio.index,
                         columns=risk_exposures_portfolio.columns)
        )

        perf_attrib_summary, exposures_summary = create_perf_attrib_stats(
            perf_attrib_output, risk_exposures_portfolio
        )

        self.assertEqual(ep.annual_return(specific_returns),
                         perf_attrib_summary['Annual multi-factor alpha'])

        self.assertEqual(ep.sharpe_ratio(specific_returns),
                         perf_attrib_summary['Multi-factor sharpe'])

        self.assertEqual(ep.cum_returns_final(specific_returns),
                         perf_attrib_summary['Cumulative specific returns'])

        self.assertEqual(ep.cum_returns_final(common_returns),
                         perf_attrib_summary['Cumulative common returns'])

        self.assertEqual(ep.cum_returns_final(combined_returns),
                         perf_attrib_summary['Total returns'])

        avg_factor_exposure = risk_exposures_portfolio.mean().rename(
            'Average Risk Factor Exposure'
        )
        pd.util.testing.assert_series_equal(
            avg_factor_exposure,
            exposures_summary['Average Risk Factor Exposure']
        )

    def test_missing_stocks_and_dates(self):

        (returns, positions,
         factor_returns, factor_loadings) = generate_toy_risk_model_output()

        # factor loadings missing a stock should raise a warning
        factor_loadings_missing_stocks = factor_loadings.drop('TLT',
                                                              level='ticker')

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            perf_attrib(returns,
                        positions,
                        factor_returns,
                        factor_loadings_missing_stocks)

            self.assertEqual(len(w), 1)
            self.assertIn("Could not find factor loadings for the following "
                          "stocks: ['TLT']", str(w[-1].message))
            self.assertIn("Coverage ratio: 2/3", str(w[-1].message))

            # missing dates should raise a warning
            missing_dates = ['2017-01-01', '2017-01-05']
            factor_loadings_missing_dates = factor_loadings.drop(missing_dates)

            exposures, perf_attrib_data =\
                perf_attrib(returns,
                            positions,
                            factor_returns,
                            factor_loadings_missing_dates)

            self.assertEqual(len(w), 2)
            self.assertIn("Could not find factor loadings for "
                          "the dates", str(w[-1].message))

            for date in missing_dates:
                self.assertNotIn(date, exposures.index)
                self.assertNotIn(date, perf_attrib_data.index)

            # perf attrib should work if factor_returns already missing dates
            exposures, perf_attrib_data = perf_attrib(
                returns,
                positions,
                factor_returns.drop(pd.DatetimeIndex(missing_dates)),
                factor_loadings_missing_dates
            )

            self.assertEqual(len(w), 3)
            self.assertIn("Could not find factor loadings for "
                          "the dates", str(w[-1].message))

            for date in missing_dates:
                self.assertNotIn(date, exposures.index)
                self.assertNotIn(date, perf_attrib_data.index)

            # test missing stocks and dates
            factor_loadings_missing_both =\
                factor_loadings_missing_dates.drop('TLT', level='ticker')

            exposures, perf_attrib_data =\
                perf_attrib(returns,
                            positions,
                            factor_returns,
                            factor_loadings_missing_both)

            self.assertEqual(len(w), 5)
            self.assertIn("Could not find factor loadings for the following "
                          "stocks: ['TLT']", str(w[-2].message))
            self.assertIn("Coverage ratio: 2/3", str(w[-2].message))

            self.assertIn("Could not find factor loadings for "
                          "the dates", str(w[-1].message))
            for date in missing_dates:
                self.assertNotIn(date, exposures.index)
                self.assertNotIn(date, perf_attrib_data.index)