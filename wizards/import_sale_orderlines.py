#-*- coding: utf-8 -*-
import base64
import io
import pandas as pd

from odoo import exceptions, fields, models, _


# Column name constants
REF_COL = 'reference'
DESC_COL = 'description'
QTY_COL = 'quantity'
PRICE_COL = 'unit_price'
DISC_COL = 'discount'

NUMERIC_COLS = {QTY_COL, PRICE_COL, DISC_COL}
TEXT_COLS = {REF_COL, DESC_COL}
REQUIRED_COLS = {*TEXT_COLS, *NUMERIC_COLS}


class ImportSaleOrderlines(models.TransientModel):
    '''ImportSaleOrderlines Wizard Model
    '''
    _name = 'import.sale.orderlines'
    _description = 'Import Sale Order Lines Wizard Model'

    name = fields.Char(string='File Name')
    file = fields.Binary(string='File', required=True)

    def import_orderlines(self):
        '''Action to process the input Excel file
        '''
        # load data from provided file
        filedata = io.BytesIO()
        filedata.write(base64.decodebytes(self.file))
        df = pd.read_excel(filedata)
        # cleaning dataset
        self._clean_imported_data(df)
        # query products
        self._query_products_by_default_code(df)
        # create new sale orderlines
        self._create_sale_orderlines(df)

    def _clean_imported_data(self, df: pd.DataFrame) -> None:
        '''_summary_

        Parameters
        ----------
        df : pd.DataFrame
            imported data from excel file

        Raises
        ------
        MissingError
            product not found
        ValidationError
            when errors occured when reading file
        '''
        self._validate_columns(df)
        # correct numeric values
        df[[*NUMERIC_COLS]] = df[[*NUMERIC_COLS]].map(pd.to_numeric, errors='coerce').fillna(0)
        # stripping whitespaces text columns
        df[[*TEXT_COLS]] = df[[*TEXT_COLS]].map(str.strip)
        # validate rows
        self._validate_rows(df)
        # remove duplicates
        df.drop_duplicates()

    def _validate_columns(self, df: pd.DataFrame) -> None:
        '''Validate dataframe contains all required columns

        Parameters
        ----------
        df : pd.DataFrame
            imported data from excel file

        Raises
        ------
        ValidationError
            raises when data is missing any required columns
        '''
        for col_name in df.columns:
            if col_name not in REQUIRED_COLS:
                raise exceptions.ValidationError(
                    _(f'Required columns: {", ".join(REQUIRED_COLS)}' )
                )

    def _validate_rows(self, df: pd.DataFrame) -> None:
        '''Validate all rows contain product reference

        Parameters
        ----------
        df : pd.DataFrame
            imported data from excel file

        Raises
        ------
        ValidationError
            raises if any row is missing reference
        '''
        invalid_rows = df[df[REF_COL].isna() | (df[QTY_COL] == 0)]
        if len(invalid_rows.index):
            raise exceptions.ValidationError(
                _('All rows must contain product reference with positive quantity.')
            )

    def _query_products_by_default_code(self, df: pd.DataFrame) -> None:
        '''Query products from references and add a new column `product_id` to dataframe

        Parameters
        ----------
        df : pd.DataFrame
            input dataset

        Raises
        ------
        ValidationError
            raises if any default code has no corresponding product
        '''
        refs = df[REF_COL].to_list()
        products = self.env['product.product'].search(
            [('default_code', 'in', refs)],
        ).read(['default_code'])
        products_map = {
            product['default_code']: product['id']
            for product in products
        }

        df['product_id'] = df[REF_COL].map(lambda ref: products_map.get(ref))

        products_not_found = df.loc[df['product_id'].isna(), REF_COL]
        if products_not_found.size > 0:
            raise exceptions.ValidationError(
                _(f'Product not found: <{products_not_found.iloc[0]}>')
            )

    def _create_sale_orderlines(self, df: pd.DataFrame) -> models.Model:
        '''Creating new sale orderlines for active order

        Parameters
        ----------
        df : pd.DataFrame
            cleaned dataset from imported file

        Returns
        -------
        models.Model :
            new SaleOrderLine recordset
        '''
        active_order_id = self._context['active_id']
        OrderLine = self.env['sale.order.line']
        new_lines = []

        for _, row in df.iterrows():
            new_lines.append({
                'order_id': active_order_id,
                'product_id': row['product_id'],
                'name': row[DESC_COL],
                'product_uom_qty': row[QTY_COL],
                'price_unit': row[PRICE_COL],
            })

        # unlink existing lines
        OrderLine.search([('order_id', '=', active_order_id)]).unlink()

        return OrderLine.create(new_lines)
